# exchanges/binance.py

import time
import hmac
import hashlib
import logging
from decimal import Decimal, ROUND_DOWN
from urllib.parse import urlencode

import requests

from config import BOOK_TICKER_ENDPOINT

logger = logging.getLogger(__name__)
trade_logger = logging.getLogger("trades")


def _round_step(value, step_str):
    step = Decimal(step_str)
    value_dec = Decimal(str(value))

    quantized = (
        value_dec / step
    ).to_integral_value(
        rounding=ROUND_DOWN
    ) * step

    return quantized


class Binance:

    BASE_URL = "https://fapi.binance.com"

    def __init__(
        self,
        api_key,
        api_secret,
        live_trading=True
    ):

        self.api_key = api_key
        self.api_secret = api_secret
        self.live_trading = live_trading

        self.session = requests.Session()

        self.session.headers.update({
            "X-MBX-APIKEY": self.api_key
        })

        self._symbol_filters_cache = {}

    # ==========================================
    # REQUEST
    # ==========================================

    def _request(
        self,
        method,
        endpoint,
        params=None,
        signed=False
    ):

        if params is None:
            params = {}

        params = dict(params)

        if signed:

            params["timestamp"] = int(
                time.time() * 1000
            )

            query_string = urlencode(params)

            signature = hmac.new(
                self.api_secret.encode(),
                query_string.encode(),
                hashlib.sha256
            ).hexdigest()

            params["signature"] = signature

        url = self.BASE_URL + endpoint

        response = self.session.request(
            method,
            url,
            params=params,
            timeout=10
        )

        if not response.ok:

            raise RuntimeError(
                f"Binance API error "
                f"{response.status_code}: "
                f"{response.text}"
            )

        return response.json()

    # ==========================================
    # POSITION
    # ==========================================

    def get_position_info(self, symbol):

        positions = self._request(
            "GET",
            "/fapi/v3/positionRisk",
            {
                "symbol": symbol
            },
            signed=True
        )

        for position in positions:

            if position["symbol"] == symbol:
                return position

        return None

    def get_position(self, symbol):

        position = self.get_position_info(symbol)

        if position is None:
            return 0.0

        amount = float(
            position["positionAmt"]
        )

        # SHORT
        if amount < 0:
            return abs(amount)

        return 0.0

    # ==========================================
    # SYMBOL FILTERS
    # ==========================================

    def _get_symbol_filters(self, symbol):

        if symbol in self._symbol_filters_cache:
            return self._symbol_filters_cache[symbol]

        info = self._request(
            "GET",
            "/fapi/v1/exchangeInfo"
        )

        for s in info["symbols"]:

            if s["symbol"] == symbol:

                filters = {
                    f["filterType"]: f
                    for f in s["filters"]
                }

                result = {
                    "tickSize":
                        filters["PRICE_FILTER"]["tickSize"],

                    "stepSize":
                        filters["LOT_SIZE"]["stepSize"],

                    "minQty":
                        filters["LOT_SIZE"]["minQty"],

                    "minNotional":
                        filters.get(
                            "MIN_NOTIONAL",
                            {}
                        ).get(
                            "notional",
                            "0"
                        )
                }

                self._symbol_filters_cache[
                    symbol
                ] = result

                return result

        raise ValueError(
            f"Символ {symbol} не найден "
            f"в Binance exchangeInfo"
        )

    # ==========================================
    # ROUND PRICE
    # ==========================================

    def round_price(
        self,
        symbol,
        price
    ):

        filters = self._get_symbol_filters(
            symbol
        )

        return _round_step(
            price,
            filters["tickSize"]
        )

    # ==========================================
    # ROUND QUANTITY
    # ==========================================

    def round_quantity(
        self,
        symbol,
        amount
    ):

        filters = self._get_symbol_filters(
            symbol
        )

        return _round_step(
            amount,
            filters["stepSize"]
        )

    # ==========================================
    # OPEN SHORT
    # ==========================================

    def open_short(
        self,
        symbol,
        amount,
        price
    ):

        if not self.live_trading:

            logger.info(
                f"[DRY RUN] OPEN SHORT "
                f"{symbol} {amount} @ {price}"
            )

            return {
                "action": "open_short",
                "symbol": symbol,
                "amount": amount,
                "live": False
            }

        rounded_price = self.round_price(
            symbol,
            price
        )

        rounded_amount = self.round_quantity(
            symbol,
            amount
        )

        params = {
            "symbol": symbol,
            "side": "SELL",
            "type": "LIMIT",
            "timeInForce": "IOC",
            "quantity": str(rounded_amount),
            "price": str(rounded_price)
        }

        logger.info(
            f"OPEN SHORT Binance: "
            f"{symbol} "
            f"qty={rounded_amount} "
            f"price={rounded_price}"
        )

        try:

            result = self._request(
                "POST",
                "/fapi/v1/order",
                params,
                signed=True
            )

        except Exception:

            logger.exception(
                f"OPEN SHORT для {symbol} "
                f"упал с ошибкой"
            )

            raise

        executed_qty = float(
            result.get(
                "executedQty",
                0
            )
        )

        if executed_qty < float(
            rounded_amount
        ):

            logger.warning(
                f"OPEN SHORT частично "
                f"исполнен: "
                f"запрошено {rounded_amount}, "
                f"исполнено {executed_qty}"
            )

        trade_logger.info(
            f"OPEN_SHORT "
            f"exchange=BINANCE "
            f"symbol={symbol} "
            f"requested={rounded_amount} "
            f"executed={executed_qty} "
            f"price={rounded_price} "
            f"orderId={result.get('orderId')}"
        )

        return result

    # ==========================================
    # CLOSE SHORT
    # ==========================================

    def close_short(
        self,
        symbol,
        amount,
        price
    ):

        if not self.live_trading:

            logger.info(
                f"[DRY RUN] CLOSE SHORT "
                f"{symbol} {amount} @ {price}"
            )

            return {
                "action": "close_short",
                "symbol": symbol,
                "amount": amount,
                "live": False
            }

        rounded_price = self.round_price(
            symbol,
            price
        )

        rounded_amount = self.round_quantity(
            symbol,
            amount
        )

        params = {
            "symbol": symbol,
            "side": "BUY",
            "type": "LIMIT",
            "timeInForce": "IOC",
            "quantity": str(rounded_amount),
            "price": str(rounded_price),
            "reduceOnly": "true"
        }

        logger.info(
            f"CLOSE SHORT Binance: "
            f"{symbol} "
            f"qty={rounded_amount} "
            f"price={rounded_price}"
        )

        try:

            result = self._request(
                "POST",
                "/fapi/v1/order",
                params,
                signed=True
            )

        except Exception:

            logger.exception(
                f"CLOSE SHORT для {symbol} "
                f"упал с ошибкой"
            )

            raise

        executed_qty = float(
            result.get(
                "executedQty",
                0
            )
        )

        if executed_qty < float(
            rounded_amount
        ):

            logger.warning(
                f"CLOSE SHORT частично "
                f"исполнен: "
                f"запрошено {rounded_amount}, "
                f"исполнено {executed_qty}"
            )

        trade_logger.info(
            f"CLOSE_SHORT "
            f"exchange=BINANCE "
            f"symbol={symbol} "
            f"requested={rounded_amount} "
            f"executed={executed_qty} "
            f"price={rounded_price} "
            f"orderId={result.get('orderId')}"
        )

        return result

    def get_price_with_buffer(self, symbol, side, buffer_pct):
        """
        Возвращает цену для IOC LIMIT ордера с буфером в вашу пользу
        по направлению сделки, чтобы ордер гарантированно исполнился
        (в пределах buffer_pct), но не улетел по стакану сильнее.

        symbol: тикер, например "CASHCATUSDT"
        side: "SELL" (открытие/увеличение шорта) или "BUY" (закрытие/уменьшение шорта)
        buffer_pct: например 0.003 = 0.3%
        """
        response = self._request(
            "GET",
            BOOK_TICKER_ENDPOINT,
            {"symbol": symbol}
        )

        bid_price = float(response["bidPrice"])
        ask_price = float(response["askPrice"])
        mid_price = (bid_price + ask_price) / 2

        if side == "SELL":
            # продаём (открываем/увеличиваем шорт) -> не хотим продать сильно
            # ниже рынка, но даём себе право уйти чуть ниже mid, чтобы
            # гарантированно исполниться против текущего bid
            price = mid_price * (1 - buffer_pct)
        elif side == "BUY":
            # откупаем (закрываем/уменьшаем шорт) -> готовы заплатить чуть
            # выше mid, чтобы гарантированно исполниться против текущего ask
            price = mid_price * (1 + buffer_pct)
        else:
            raise ValueError(f"Неизвестный side: {side}")

        return price

    def get_trade_history(self, symbol, hours=48):

        end_time = int(time.time() * 1000)
        start_time = end_time - (hours * 60 * 60 * 1000)

        all_trades = []

        window = 12 * 60 * 60 * 1000
        current_start = start_time

        while current_start < end_time:
            current_end = min(
                current_start + window - 1,
                end_time
            )

            params = {
                "symbol": symbol,
                "startTime": current_start,
                "endTime": current_end,
                "limit": 1000,
            }

            trades = self._request(
                "GET",
                "/fapi/v1/userTrades",
                params,
                signed=True,  # <-- вот чего не хватало
            )

            all_trades.extend(trades)

            current_start = current_end + 1

        unique = {}
        for trade in all_trades:
            unique[trade["id"]] = trade

        return sorted(unique.values(), key=lambda x: x["time"])