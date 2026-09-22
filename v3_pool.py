from abi.v3_view import V3_POOL_ABI


class V3Pool:

    def __init__(self, rpc, pool_address):

        self.rpc = rpc

        self.address = pool_address

        self.contract = rpc.contract(
            pool_address,
            V3_POOL_ABI
        )

    def slot0(self):
        return self.contract.functions.slot0().call()

    def liquidity(self):
        return self.contract.functions.liquidity().call()

    def token0(self):
        return self.contract.functions.token0().call()

    def token1(self):
        return self.contract.functions.token1().call()

    def fee(self):
        return self.contract.functions.fee().call()

    def info(self):

        slot = self.slot0()

        return {
            "sqrtPriceX96": slot[0],
            "tick": slot[1],
            "liquidity": self.liquidity(),
            "token0": self.token0(),
            "token1": self.token1(),
            "fee": self.fee()
        }