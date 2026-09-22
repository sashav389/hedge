from abi.v3_view import V3_POSITION_MANAGER_ABI
from config import V3_POSITION_MANAGER_BSC


class V3Position:

    def __init__(self, rpc, manager):

        self.rpc = rpc

        self.manager = rpc.contract(
            manager,
            V3_POSITION_MANAGER_ABI
        )

    def get_position(self, token_id):
        print("TOKEN ID:", token_id)
        print("TOKEN ID TYPE:", type(token_id))
        print("MANAGER:", self.manager.address)

        position = self.manager.functions.positions(
            token_id
        ).call()

        return {
            "tokenId": token_id,
            "nonce": position[0],
            "operator": position[1],
            "token0": position[2],
            "token1": position[3],
            "fee": position[4],
            "tickLower": position[5],
            "tickUpper": position[6],
            "liquidity": position[7],
            "feeGrowthInside0LastX128": position[8],
            "feeGrowthInside1LastX128": position[9],
            "tokensOwed0": position[10],
            "tokensOwed1": position[11],
        }
