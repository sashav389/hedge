from eth_account import Account

from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants


class Hyperliquid:

    def __init__(self, wallet_address, private_key):

        self.wallet_address = wallet_address

        self.info = Info(
            constants.MAINNET_API_URL,
            skip_ws=True
        )

        wallet = Account.from_key(private_key)

        self.exchange = Exchange(
            wallet,
            constants.MAINNET_API_URL,
            account_address=wallet_address
        )

    def get_position(self, symbol):

        state = self.info.user_state(
            self.wallet_address
        )

        for item in state["assetPositions"]:

            position = item["position"]

            if position["coin"] == symbol:

                size = float(position["szi"])

                if size < 0:
                    return abs(size)

                return 0.0

        return 0.0

    def open_short(self, symbol, amount):

        print(
            f"OPEN SHORT: {amount} {symbol}"
        )

        result = self.exchange.market_open(
            symbol,
            False,
            amount
        )

        print("Hyperliquid response:")
        print(result)

        return result

    def close_short(self, symbol, amount):

        print(
            f"CLOSE SHORT: {amount} {symbol}"
        )

        result = self.exchange.market_close(
            symbol,
            sz=amount
        )

        print("Hyperliquid response:")
        print(result)

        return result