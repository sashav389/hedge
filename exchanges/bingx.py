"""
bingx.py

Адаптер BingX USDT-M Perpetual Futures под тот же интерфейс, что Aster,
чтобы объект Hedge мог работать с обеими биржами без изменений в hedge.py.

Официальная документация:
    https://bingx-api.github.io/docs/#/swapV2/introduce

Установка:
    pip install requests

ВАЖНО - отличия от Aster, на которые стоит обратить внимание:
  - Символ передаётся с дефисом: "CASHCAT-USDT", а не "CASHCATUSDT".
  - BingX работает в hedge-mode: направление позиции (LONG/SHORT) и
    направление ордера (BUY/SELL) - два разных параметра. Открытие шорта:
    side=SELL, positionSide=SHORT. Закрытие шорта: side=BUY, positionSide=SHORT.
    (в отличие от Aster, где было reduceOnly=true).
  - Precision у контрактов задаётся числом знаков после запятой
    (quantityPrecision/pricePrecision), а не строкой шага (tickSize/stepSize
    как у Aster) - соответственно другой алгоритм округления.
  - Подпись - обычный HMAC-SHA256 по отсортированным параметрам с секретным
    ключом, передаётся в query string, API-ключ - в заголовке X-BX-APIKEY.
"""

import hashlib
import hmac
import logging
import time

import requests

logger = logging.getLogger(__name__)
trade_logger = logging.getLogger("trades")


class BingX:
    BASE_URL = "https://open-api.bingx.com"

    def __init__(
            self,
            api_key,
            api_secret,
            live_trading=True
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.live_trading = live_trading

        self._contract_cache = {}

    # ------------------------------------------------------------
    # ПОДПИСЬ И ЗАПРОСЫ
    # ------------------------------------------------------------

    def _sign(self, params_str: str) -> str:
        return hmac.new(
            self.api_secret.encode("utf-8"),
            params_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _build_params_str(self, params: dict) -> str:
        """Сортируем параметры по ключу, добавляем timestamp в конец - именно
        так требует BingX (timestamp не участвует в сортировке)."""
        sorted_keys = sorted(params.keys())
        parts = [f"{key}={params[key]}" for key in sorted_keys]
        params_str = "&".join(parts)
        timestamp = str(int(time.time() * 1000))
        return params_str + "&timestamp=" + timestamp

    def _request(self, method, endpoint, params=None):
        if params is None:
            params = {}

        params_str = self._build_params_str(params)
        signature = self._sign(params_str)

        url = f"{self.BASE_URL}{endpoint}?{params_str}&signature={signature}"

        headers = {
            "X-BX-APIKEY": self.api_key,
        }

        response = requests.request(method, url, headers=headers, timeout=10)

        if not response.ok:
            raise RuntimeError(
                f"BingX API error {response.status_code}: {response.text}"
            )

        data = response.json()

        # BingX оборачивает ответ в {"code": 0, "msg": "", "data": {...}}
        if data.get("code") not in (0, None):
            raise RuntimeError(f"BingX API вернул ошибку: {data}")

        return data.get("data", data)

    # ------------------------------------------------------------
    # ПОЗИЦИИ
    # ------------------------------------------------------------

    def get_position(self, symbol):
        """
        Возвращает текущий размер ШОРТА по symbol (положительное число).
        Если позиции нет или она в лонге - возвращает 0.0.

        symbol: формат BingX, например "CASHCAT-USDT"
        """
        positions = self._request(
            "GET",
            "/openApi/swap/v2/user/positions",
            {"symbol": symbol},
        )

        for position in positions:
            if position.get("symbol") != symbol:
                continue
            if position.get("positionSide") != "SHORT":
                continue

            amount = float(position.get("positionAmt", 0))
            return abs(amount)

        return 0.0

    # ------------------------------------------------------------
    # PRECISION / ОКРУГЛЕНИЕ
    # ------------------------------------------------------------

    def _get_contract_precision(self, symbol):
        if symbol in self._contract_cache:
            return self._contract_cache[symbol]

        contracts = self._request(
            "GET",
            "/openApi/swap/v2/quote/contracts",
            {},
        )

        for contract in contracts:
            if contract.get("symbol") == symbol:
                result = {
                    "quantityPrecision": int(contract["quantityPrecision"]),
                    "pricePrecision": int(contract["pricePrecision"]),
                }
                self._contract_cache[symbol] = result
                return result

        raise ValueError(f"Символ {symbol} не найден в /quote/contracts")

    def round_price(self, symbol, price):
        precision = self._get_contract_precision(symbol)
        return round(float(price), precision["pricePrecision"])

    def round_quantity(self, symbol, amount):
        precision = self._get_contract_precision(symbol)
        return round(float(amount), precision["quantityPrecision"])

    # ------------------------------------------------------------
    # ЦЕНА С БУФЕРОМ (аналог Aster get_price_with_buffer)
    # ------------------------------------------------------------

    def get_price_with_buffer(self, symbol, side, buffer_pct):
        """
        symbol: "CASHCAT-USDT"
        side: "SELL" (открытие/увеличение шорта) или "BUY" (закрытие/уменьшение шорта)
        buffer_pct: например 0.003 = 0.3%
        """
        response = self._request(
            "GET",
            "/openApi/swap/v2/quote/bookTicker",
            {"symbol": symbol},
        )

        bid_price = float(response["bidPrice"])
        ask_price = float(response["askPrice"])
        mid_price = (bid_price + ask_price) / 2

        if side == "SELL":
            price = mid_price * (1 - buffer_pct)
        elif side == "BUY":
            price = mid_price * (1 + buffer_pct)
        else:
            raise ValueError(f"Неизвестный side: {side}")

        return price

    # ------------------------------------------------------------
    # ОТКРЫТИЕ / ЗАКРЫТИЕ ШОРТА
    # ------------------------------------------------------------

    def open_short(self, symbol, amount, price):
        """Открыть/увеличить шорт. side=SELL, positionSide=SHORT (hedge-mode)."""

        if not self.live_trading:
            logger.info(f"[DRY RUN] OPEN SHORT {symbol} {amount} @ {price}")
            return {
                "action": "open_short",
                "symbol": symbol,
                "amount": amount,
                "live": False,
            }

        rounded_price = self.round_price(symbol, price)
        rounded_amount = self.round_quantity(symbol, amount)

        params = {
            "symbol": symbol,
            "side": "SELL",
            "positionSide": "SHORT",
            "type": "LIMIT",
            "timeInForce": "IOC",
            "quantity": str(rounded_amount),
            "price": str(rounded_price),
        }

        logger.info(
            f"OPEN SHORT запрос: {symbol} qty={rounded_amount} "
            f"min_price={rounded_price} (raw: qty={amount} price={price})"
        )

        try:
            result = self._request("POST", "/openApi/swap/v2/trade/order", params)
        except Exception:
            logger.exception(f"OPEN SHORT для {symbol} упал с ошибкой")
            raise

        trade_logger.info(
            f"OPEN_SHORT symbol={symbol} requested={rounded_amount} "
            f"price={rounded_price} raw_result={result}"
        )

        return result

    def close_short(self, symbol, amount, price):
        """Закрыть/уменьшить шорт. side=BUY, positionSide=SHORT (hedge-mode -
        BingX сам понимает, что BUY при positionSide=SHORT это закрытие,
        отдельный reduceOnly флаг не нужен)."""

        if not self.live_trading:
            logger.info(f"[DRY RUN] CLOSE SHORT {symbol} {amount} @ {price}")
            return {
                "action": "close_short",
                "symbol": symbol,
                "amount": amount,
                "live": False,
            }

        rounded_price = self.round_price(symbol, price)
        rounded_amount = self.round_quantity(symbol, amount)

        params = {
            "symbol": symbol,
            "side": "BUY",
            "positionSide": "SHORT",
            "type": "LIMIT",
            "timeInForce": "IOC",
            "quantity": str(rounded_amount),
            "price": str(rounded_price),
        }

        logger.info(f"CLOSE SHORT запрос: {symbol} qty={rounded_amount} max_price={rounded_price}")

        try:
            result = self._request("POST", "/openApi/swap/v2/trade/order", params)
        except Exception:
            logger.exception(f"CLOSE SHORT для {symbol} упал с ошибкой")
            raise

        trade_logger.info(
            f"CLOSE_SHORT symbol={symbol} requested={rounded_amount} "
            f"price={rounded_price} raw_result={result}"
        )

        return result