from web3 import Web3


class RPC:

    def __init__(self, RPC_link):

        self.w3 = Web3(Web3.HTTPProvider(RPC_link))

        if not self.w3.is_connected():
            raise RuntimeError("RPC connection failed")

        print("Connected")

    def contract(self, address, abi):
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(address),
            abi=abi
        )


    @property
    def block(self):
        return self.w3.eth.block_number

    def balance(self, address):
        return self.w3.eth.get_balance(
            Web3.to_checksum_address(address)
        )

    def code(self, address):
        return self.w3.eth.get_code(
            Web3.to_checksum_address(address)
        )


