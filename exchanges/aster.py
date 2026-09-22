import time
import urllib.parse
import requests
import logging

from eth_account import Account
from eth_account.messages import encode_typed_data
from decimal import Decimal, ROUND_DOWN

from config import BOOK_TICKER_ENDPOINT

logger = logging.getLogger(__name__)
trade_logger = logging.getLogger("trades")


def _get_nonce():
    return int(time.time() * 1_000_000)


def _round_step(value, step_str):
    """Округляем value вниз до ближайшего кратного step_str, через Decimal (без ошибок float)."""
    step = Decimal(step_str)
    value_dec = Decimal(str(value))
    quantized = (value_dec / step).to_integral_value(rounding=ROUND_DOWN) * step
    return quantized


class Aster:
    BASE_URL = "https://fapi.asterdex.com"

    def __init__(
            self,
            user,
            signer,
            private_key,
            live_trading=True
    ):

        self.user = user
        self.signer = signer
        self.private_key = private_key

        self.live_trading = live_trading

        account = Account.from_key(private_key)

        self.account = account
        self._nonce_counter = 0

    def get_position_info(self, symbol):

        positions = self._request(
            "GET",
            "/fapi/v3/positionRisk",
            {
                "symbol": symbol
            }
        )

        for position in positions:

            if position["symbol"] == symbol:
                return position

        return None

    def _sign(self, message_body):

        typed_data = {
            "types": {
                "EIP712Domain": [
                    {
                        "name": "name",
                        "type": "string"
                    },
                    {
                        "name": "version",
                        "type": "string"
                    },
                    {
                        "name": "chainId",
                        "type": "uint256"
                    },
                    {
                        "name": "verifyingContract",
                        "type": "address"
                    }
                ],
                "Message": [
                    {
                        "name": "msg",
                        "type": "string"
                    }
                ]
            },

            "primaryType": "Message",

            "domain": {
                "name": "AsterSignTransaction",
                "version": "1",
                "chainId": 1666,
                "verifyingContract":
                    "0x0000000000000000000000000000000000000000"
            },

            "message": {
                "msg": message_body
            }
        }

        encoded = encode_typed_data(
            full_message=typed_data
        )

        signed = self.account.sign_message(
            encoded
        )

        return signed.signature.hex()

    def _request(self, method, endpoint, params=None):

        if params is None:
            params = {}

        nonce = str(_get_nonce())

        # Порядок именно такой
        request_params = {
            "nonce": nonce,
            "user": self.user,
            "signer": self.signer,
        }

        # Остальные параметры добавляем после обязательных
        for key, value in params.items():
            request_params[key] = value

        # Это именно message body, который подписываем
        message_body = urllib.parse.urlencode(
            request_params
        )

        print()
        print("MESSAGE BODY:")
        print(message_body)

        signature = self._sign(message_body)

        print()
        print("SIGNATURE:")
        print(signature)

        # signature НЕ входит в подписываемый message
        request_params["signature"] = signature

        url = self.BASE_URL + endpoint

        response = requests.request(
            method,
            url,
            params=request_params,
            timeout=10
        )

        if not response.ok:
            raise RuntimeError(
                f"Aster API error "
                f"{response.status_code}: "
                f"{response.text}"
            )

        return response.json()

    # ==========================================
    # POSITIONS
    # ==========================================

    def get_positions(self):

        return self._request(
            "GET",
            "/fapi/v3/positionRisk"
        )

    def get_position(self, symbol):

        positions = self._request(
            "GET",
            "/fapi/v3/positionRisk",
            {
                "symbol": symbol
            }
        )

        for position in positions:

            if position["symbol"] == symbol:

                amount = float(
                    position["positionAmt"]
                )

                if amount < 0:
                    return abs(amount)

                return 0.0

        return 0.0

    def _get_symbol_filters(self, symbol):
        """Кэшируем tickSize/stepSize по символу, чтобы не дёргать exchangeInfo на каждый ордер."""
        if not hasattr(self, "_symbol_filters_cache"):
            self._symbol_filters_cache = {}

        if symbol in self._symbol_filters_cache:
            return self._symbol_filters_cache[symbol]

        info = self._request("GET", "/fapi/v1/exchangeInfo", {})

        for s in info["symbols"]:
            if s["symbol"] == symbol:
                filters = {f["filterType"]: f for f in s["filters"]}
                result = {
                    "tickSize": filters["PRICE_FILTER"]["tickSize"],
                    "stepSize": filters["LOT_SIZE"]["stepSize"],
                }
                self._symbol_filters_cache[symbol] = result
                return result

        raise ValueError(f"Символ {symbol} не найден в exchangeInfo")

    def round_price(self, symbol, price):
        filters = self._get_symbol_filters(symbol)
        return _round_step(price, filters["tickSize"])

    def open_short(
            self,
            symbol,
            amount,
            price
    ):

        if not self.live_trading:
            logger.info(f"[DRY RUN] OPEN SHORT {symbol} {amount} @ {price}")

            return {
                "action": "open_short",
                "symbol": symbol,
                "amount": amount,
                "live": False
            }

        rounded_price = self.round_price(symbol, price)

        params = {
            "symbol": symbol,
            "side": "SELL",
            "type": "LIMIT",
            "timeInForce": "IOC",
            "quantity": str(amount),
            "price": str(rounded_price),

        }

        logger.info(
            f"OPEN SHORT запрос: {symbol} qty={amount} "
            f"min_price={rounded_price} (raw: qty={amount} price={price})"
        )

        try:
            result = self._request("POST", "/fapi/v3/order", params)
        except Exception:
            logger.exception(f"OPEN SHORT для {symbol} упал с ошибкой")
            raise

        executed_qty = float(result.get("executedQty", 0))
        if executed_qty < float(amount):
            logger.warning(
                f"OPEN SHORT частично исполнен: запрошено {amount}, "
                f"исполнено {executed_qty}"
            )

        trade_logger.info(
            f"OPEN_SHORT symbol={symbol} requested={amount} "
            f"executed={executed_qty} price={rounded_price} orderId={result.get('orderId')}"
        )

        return result

    def close_short(
            self,
            symbol,
            amount,
            price
    ):

        if not self.live_trading:
            logger.info(f"[DRY RUN] CLOSE SHORT {symbol} {amount} @ {price}")

            return {
                "action": "close_short",
                "symbol": symbol,
                "amount": amount,
                "live": False
            }

        rounded_price = self.round_price(symbol, price)

        params = {
            "symbol": symbol,
            "side": "BUY",
            "type": "LIMIT",
            "timeInForce": "IOC",
            "quantity": str(amount),
            "price": str(rounded_price),
            "reduceOnly": "true",
        }

        logger.info(f"CLOSE SHORT запрос: {symbol} qty={amount} max_price={rounded_price}")

        try:
            result = self._request("POST", "/fapi/v3/order", params)
        except Exception:
            logger.exception(f"CLOSE SHORT для {symbol} упал с ошибкой")
            raise

        executed_qty = float(result.get("executedQty", 0))
        if executed_qty < amount:
            logger.warning(
                f"CLOSE SHORT частично исполнен: запрошено {amount}, "
                f"исполнено {executed_qty}"
            )

        trade_logger.info(
            f"CLOSE_SHORT symbol={symbol} requested={amount} "
            f"executed={executed_qty} price={rounded_price} orderId={result.get('orderId')}"
        )

        return result

    # сверьте с docs.asterdex.com перед запуском

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
