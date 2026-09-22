from config import LIVE_TRADING


class Hedge:

    def __init__(self, exchange, symbol, threshold=0.003):

        self.exchange = exchange
        self.symbol = symbol
        self.threshold = threshold

    def calculate(self, lp_amount):

        current_short = self.exchange.get_position(
            self.symbol
        )

        target_short = lp_amount

        delta = target_short - current_short

        if target_short == 0:
            deviation = 0
        else:
            deviation = abs(delta) / target_short

        return {
            "lp_amount": lp_amount,
            "current_short": current_short,
            "target_short": target_short,
            "delta": delta,
            "deviation": deviation,
        }

    def rebalance(self, lp_amount):
        result = self.calculate(lp_amount)
        delta = result["delta"]
        deviation = result["deviation"]

        # =========================
        # THRESHOLD
        # =========================
        if deviation < self.threshold:
            result["action"] = "NOTHING"
            result["amount"] = 0
            return result

        # =========================
        # ROUND TO INTEGER
        # =========================
        amount = int(abs(delta))
        if amount <= 0:
            result["action"] = "NOTHING"
            result["amount"] = 0
            return result

        # =========================
        # DETERMINE ACTION
        # =========================
        if delta > 0:
            action = "INCREASE SHORT"
        else:
            action = "DECREASE SHORT"

        result["action"] = action
        result["amount"] = amount

        BUFFER_PCT = 0.001
        if delta > 0:
            price = self.exchange.get_price_with_buffer(self.symbol, "SELL", BUFFER_PCT)
            self.exchange.open_short(
                self.symbol,
                amount,
                price
            )
        else:
            price = self.exchange.get_price_with_buffer(self.symbol, "BUY", BUFFER_PCT)
            self.exchange.close_short(
                self.symbol,
                amount,
                price
            )

        return result
