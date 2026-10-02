"""
ladder.py

Лестница STOP_MARKET ордеров на бирже, повторяющая кривую LP-позиции.

Идея: количество token0 в позиции x(P) - известная функция цены. Значит,
заранее можно выставить на бирже:
  - BUY стопы выше цены (reduceOnly) - откупают шорт, когда цена растёт;
  - SELL стопы ниже цены - добавляют шорт, когда цена падает.
Биржа сама срабатывает в момент движения, без задержки блок -> WS -> REST.

Цена триггера учитывает no-arb коридор пула: арбитражёр двигает пул только
когда биржа ушла дальше комиссии пула f. Пул дойдёт до цены P, когда биржа
будет на P*(1+f) при росте и на P*(1-f) при падении. Поэтому:
  BUY  trigger = P * basis * (1 + band)
  SELL trigger = P * basis * (1 - band)
Это же даёт гистерезис 2*band между BUY и SELL ступенями - лестница
не "пилит" туда-обратно, пока пул стоит на месте.

Своп-события и таймер делают сверку: целевой шорт считается от ОЖИДАЕМОЙ
цены пула (цена пула, зажатая в коридор вокруг биржи), и если шорт ушёл
от цели больше чем на reconcile_frac ступени - доводим IOC ордером, как раньше.

dry_run=True: ничего не выставляет, старая логика хеджа работает как была,
лестница только печатает, что бы она выставила.
"""

import threading
import time
from decimal import Decimal

from uniswap.v3_math import (
    amount0_at_price,
    max_amount0,
    price_at_amount0,
    sqrt_price_x96_to_price,
)


# стопы с таким префиксом clientId считаются своими, остальные не трогаем
CLIENT_ID_PREFIX = "hl"


DEFAULTS = {
    "enabled": False,
    "dry_run": True,

    # шаг лестницы по цене: 0.0025 = ступень на каждые 0.25% движения
    "rung_pct": 0.0025,

    # ступеней на каждую сторону (у Aster лимит 10 стопов на символ)
    "levels": 4,

    # ширина no-arb коридора; None -> комиссия пула
    "band": None,

    # биржа / пул в равновесии (перп-премия); 1.0 = без базиса
    "basis": 1.0,

    "working_type": "CONTRACT_PRICE",
    "price_protect": True,

    # сверка IOC, если шорт ушёл от цели больше чем на 0.6 ступени
    "reconcile_frac": 0.6,

    # не перевыставлять стоп, если триггер сдвинулся меньше чем на 0.05%
    "reprice_tol": 0.0005,

    "resync_sec": 5,
}


class Ladder:

    def __init__(self, name, exchange, hedge, symbol, pool_fee, config):

        cfg = dict(DEFAULTS)
        cfg.update(config or {})

        self.cfg = cfg
        self.name = name
        self.exchange = exchange
        self.hedge = hedge
        self.symbol = symbol

        # fee пула в сотых долях бипа: 3000 -> 0.003
        self.band = cfg["band"] if cfg["band"] is not None else pool_fee / 1_000_000

        self.dry_run = cfg["dry_run"]
        self.resync_sec = cfg["resync_sec"]

        self.liquidity = 0
        self.tick_lower = None
        self.tick_upper = None
        self.x_max = 0
        self.p_lower = None
        self.p_upper = None

        self.pool_price = None

        # размер ступени в токенах; фиксируем на позицию,
        # иначе от округления все стопы перевыставлялись бы
        self.q = None

        self._lock = threading.Lock()
        self._last_preview = None
        self._id_counter = 0

    # ========================================================
    # STATE
    # ========================================================

    def set_position(self, liquidity, tick_lower, tick_upper):

        self.liquidity = liquidity
        self.tick_lower = tick_lower
        self.tick_upper = tick_upper
        self.q = None

        if liquidity:
            self.x_max = max_amount0(liquidity, tick_lower, tick_upper)
            self.p_lower = self._price(self.x_max)
            self.p_upper = self._price(0)

    def set_pool_price(self, sqrt_price_x96):
        self.pool_price = sqrt_price_x96_to_price(sqrt_price_x96)

    # ========================================================
    # ENTRY POINTS
    # ========================================================

    def on_swap(self, sqrt_price_x96):

        prev_price = self.pool_price
        self.set_pool_price(sqrt_price_x96)

        with self._lock:
            return self._step(prev_price, verbose=True)

    def resync(self):

        if self.pool_price is None:
            return None

        # своп-событие уже в работе - пропускаем тик таймера
        if not self._lock.acquire(blocking=False):
            return None

        try:
            return self._step(None, verbose=False)
        finally:
            self._lock.release()

    def cancel_all(self):

        with self._lock:
            self._sync([])

    # ========================================================
    # CORE
    # ========================================================

    def _step(self, prev_price, verbose):

        if not self.liquidity:
            # позиция закрыта - снимаем свои стопы
            if not self.dry_run:
                self._sync([])
            return None

        bid, ask = self.exchange.get_book(self.symbol)
        mid = (bid + ask) / 2

        pool = self.pool_price
        basis = self.cfg["basis"]
        band = self.band

        # пул догонит биржу только до края коридора
        expected = min(
            max(pool, mid / (basis * (1 + band))),
            mid / (basis * (1 - band))
        )

        target = self._x(expected)

        if self.q is None or self.q < self._min_qty(expected):
            self.q = self._rung_qty(expected)

        q = self.q

        state = {
            "pool": pool,
            "mid": mid,
            "expected": expected,
            "target": target,
            "q": q,
        }

        # сразу после арбитражного свопа пул стоит на краю коридора:
        # mid / pool = basis * (1 ± band) -> оценка basis для калибровки
        if prev_price and pool != prev_price:
            edge = (1 + band) if pool > prev_price else (1 - band)
            state["basis_est"] = mid / pool / edge

        if self.dry_run:
            short = self.exchange.get_position(self.symbol)
        else:
            result = self.hedge.rebalance(
                target,
                min_delta=self.cfg["reconcile_frac"] * q
            )

            short = result["current_short"]

            if result["action"] != "NOTHING":
                short = self.exchange.get_position(self.symbol)

            state["reconcile"] = f'{result["action"]} {result["amount"]}'

        state["short"] = short

        rungs = self._build_rungs(short, q, mid) if q > 0 else []

        if self.dry_run:
            self._preview(state, rungs, verbose)
        else:
            if verbose:
                self._print_state(state)
            self._sync(rungs)

        return state

    def _rung_qty(self, price):

        # считаем ступень внутри диапазона, даже если цена сейчас вне его
        rung_pct = self.cfg["rung_pct"]
        p = min(max(price, self.p_lower), self.p_upper / (1 + rung_pct))

        q = self._x(p) - self._x(p * (1 + rung_pct))

        return float(
            self.exchange.round_quantity(
                self.symbol,
                max(q, self._min_qty(price))
            )
        )

    def _min_qty(self, price):

        filters = self.exchange._get_symbol_filters(self.symbol)

        # каждая ступень должна проходить minQty и minNotional
        return max(
            float(filters["minQty"]),
            float(filters["minNotional"]) * 1.1 / price
        )

    def _build_rungs(self, short, q, mid):

        basis = self.cfg["basis"]
        guard = mid * 0.0002

        rungs = []

        # BUY: цена растёт -> токена в LP меньше -> откупаем шорт
        # SELL: цена падает -> токена в LP больше -> добавляем шорт
        for side, direction, edge in (
            ("BUY", -1, 1 + self.band),
            ("SELL", 1, 1 - self.band),
        ):

            before = short

            for _ in range(self.cfg["levels"]):

                after = min(max(before + direction * q, 0), self.x_max)

                qty = self.exchange.round_quantity(
                    self.symbol,
                    (after - before) * direction
                )

                if qty <= 0:
                    break

                after = before + direction * float(qty)

                # переключаемся на середине между уровнями шорта:
                # ошибка хеджа не больше половины ступени
                pool_trigger = self._price((before + after) / 2)

                trigger = self.exchange.round_price(
                    self.symbol,
                    pool_trigger * basis * edge
                )

                before = after

                # стоп по ту сторону цены сработал бы сразу -
                # это работа для сверки, а не для лестницы
                if side == "BUY" and float(trigger) <= mid + guard:
                    continue

                if side == "SELL" and float(trigger) >= mid - guard:
                    continue

                rungs.append({
                    "side": side,
                    "qty": qty,
                    "trigger": trigger,
                    "pool_trigger": pool_trigger,
                })

        rungs.sort(key=lambda r: r["trigger"], reverse=True)

        return rungs

    def _sync(self, rungs):

        existing = [
            o for o in self.exchange.get_open_stops(self.symbol)
            if o["client_id"].startswith(CLIENT_ID_PREFIX)
        ]

        tol = Decimal(str(self.cfg["reprice_tol"]))

        to_place = []

        for rung in rungs:

            match = next(
                (
                    o for o in existing
                    if o["side"] == rung["side"]
                    and o["qty"] == rung["qty"]
                    and abs(o["trigger"] / rung["trigger"] - 1) <= tol
                ),
                None
            )

            if match is not None:
                existing.remove(match)
            else:
                to_place.append(rung)

        # сначала снимаем лишние - чтобы не упереться в лимит стопов
        for order in existing:
            try:
                self.exchange.cancel_stop(self.symbol, order["id"])
                print(
                    f"[{self.name}] LADDER CANCEL {order['side']} "
                    f"{order['qty']} @ {order['trigger']}"
                )
            except Exception as e:
                print(f"[{self.name}] LADDER CANCEL ERROR: {e}")

        for rung in to_place:
            try:
                self.exchange.place_stop(
                    self.symbol,
                    rung["side"],
                    rung["qty"],
                    rung["trigger"],
                    self._client_id(rung["side"]),
                    reduce_only=rung["side"] == "BUY",
                    working_type=self.cfg["working_type"],
                    price_protect=self.cfg["price_protect"],
                )
                print(
                    f"[{self.name}] LADDER PLACE {rung['side']} "
                    f"{rung['qty']} @ {rung['trigger']}"
                )
            except Exception as e:
                print(f"[{self.name}] LADDER PLACE ERROR: {e}")

    # ========================================================
    # HELPERS
    # ========================================================

    def _x(self, price):
        return amount0_at_price(
            self.liquidity, price, self.tick_lower, self.tick_upper
        )

    def _price(self, amount0):
        return price_at_amount0(
            self.liquidity, amount0, self.tick_lower, self.tick_upper
        )

    def _client_id(self, side):
        self._id_counter += 1
        return (
            f"{CLIENT_ID_PREFIX}{side[0]}"
            f"{int(time.time() * 1000)}{self._id_counter % 1000:03d}"
        )

    def _print_state(self, state):

        line = (
            f"[{self.name}] LADDER{' DRY-RUN' if self.dry_run else ''} "
            f"pool={state['pool']:.7f} "
            f"cex={state['mid']:.7f} "
            f"({(state['mid'] / state['pool'] - 1) * 100:+.3f}%) "
            f"band={self.band * 100:.2f}% "
            f"basis={self.cfg['basis']:.4f} "
            f"expected={state['expected']:.7f} "
            f"target={state['target']:.1f} "
            f"short={state['short']} "
            f"q={state['q']:g}"
        )

        if "basis_est" in state:
            line += f" basis_est={state['basis_est']:.4f}"

        if "reconcile" in state:
            line += f" reconcile={state['reconcile']}"

        print(line)

    def _preview(self, state, rungs, verbose):

        snapshot = [(r["side"], r["qty"], r["trigger"]) for r in rungs]

        if not verbose and snapshot == self._last_preview:
            return

        self._last_preview = snapshot

        self._print_state(state)

        for r in rungs:
            print(
                f"    {r['side']:<4} {r['qty']:>10} @ {r['trigger']}"
                f"   (пул {r['pool_trigger']:.7f})"
            )
