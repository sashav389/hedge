"""
v4_pool.py

Аналог v3_pool.py, но под архитектуру Uniswap V4.

Ключевое отличие от V3: у пула НЕТ собственного адреса контракта. Вместо
этого:
  1. Пул идентифицируется через PoolId = keccak256(abi.encode(PoolKey)),
     где PoolKey = (currency0, currency1, fee, tickSpacing, hooks).
     currency0/currency1 должны быть отсортированы по возрастанию адреса
     (V4 требует currency0 < currency1, как и V3 требует token0 < token1).
  2. Всё состояние пулов физически хранится в одном singleton-контракте
     PoolManager, но читать его напрямую неудобно (extsload). Поэтому
     используется официальный периферийный контракт StateView, который
     предоставляет удобные view-функции getSlot0(poolId)/getLiquidity(poolId).

ВАЖНО:
  - STATE_VIEW_ADDRESS - это АДРЕС ПЕРИФЕРИЙНОГО КОНТРАКТА StateView,
    НЕ адрес PoolManager и НЕ адрес пула. У каждой сети/деплоя V4 свой
    адрес StateView - возьмите его из официальной документации Uniswap
    для вашей конкретной сети, либо (если это форк V4 на нестандартной
    сети типа Robinhood Chain) - уточните у документации/support этой сети,
    задеплоен ли там вообще StateView-эквивалент.
  - fee в PoolKey - это СТАТИЧЕСКИЙ параметр, использованный при
    инициализации пула (может быть флагом динамической комиссии,
    0x800000). Актуальную комиссию прямо сейчас (для динамических
    fee-хуков) нужно брать из lpFee в ответе getSlot0(), а не из fee
    в PoolKey - в info() возвращены оба значения.
"""

from eth_abi import encode
from web3 import Web3

from abi.v4_view import V4_STATE_VIEW_ABI


ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


def compute_pool_id(currency0, currency1, fee, tick_spacing, hooks=ZERO_ADDRESS):
    """
    Считает PoolId так же, как это делает Uniswap V4 SDK (Pool.getPoolId).
    Автоматически сортирует currency0/currency1 по возрастанию адреса -
    V4 требует currency0 < currency1, как и V3 требует token0 < token1.
    """
    c0 = Web3.to_checksum_address(currency0)
    c1 = Web3.to_checksum_address(currency1)

    if int(c0, 16) > int(c1, 16):
        c0, c1 = c1, c0

    hooks_checksum = Web3.to_checksum_address(hooks)

    encoded = encode(
        ["address", "address", "uint24", "int24", "address"],
        [c0, c1, fee, tick_spacing, hooks_checksum],
    )

    return Web3.keccak(encoded)


class V4Pool:

    def __init__(
            self,
            rpc,
            state_view_address,
            currency0,
            currency1,
            fee,
            tick_spacing,
            hooks=ZERO_ADDRESS,
    ):
        self.rpc = rpc

        self.state_view_address = state_view_address

        # сортируем сразу, чтобы currency0/currency1 в объекте всегда
        # совпадали с тем, что реально ушло в расчёт PoolId
        c0 = Web3.to_checksum_address(currency0)
        c1 = Web3.to_checksum_address(currency1)
        if int(c0, 16) > int(c1, 16):
            c0, c1 = c1, c0

        self.currency0 = c0
        self.currency1 = c1
        self.fee = fee
        self.tick_spacing = tick_spacing
        self.hooks = Web3.to_checksum_address(hooks)

        self.pool_id = compute_pool_id(
            self.currency0,
            self.currency1,
            self.fee,
            self.tick_spacing,
            self.hooks,
        )

        self.contract = rpc.contract(
            state_view_address,
            V4_STATE_VIEW_ABI,
        )

    def slot0(self):
        return self.contract.functions.getSlot0(self.pool_id).call()

    def liquidity(self):
        return self.contract.functions.getLiquidity(self.pool_id).call()

    def info(self):

        slot = self.slot0()

        return {
            "sqrtPriceX96": slot[0],
            "tick": slot[1],
            "protocolFee": slot[2],
            "lpFee": slot[3],           # актуальная комиссия сейчас (важно для dynamic fee)
            "liquidity": self.liquidity(),
            "token0": self.currency0,
            "token1": self.currency1,
            "fee": self.fee,            # статический параметр из PoolKey
            "tickSpacing": self.tick_spacing,
            "hooks": self.hooks,
            "poolId": self.pool_id.hex(),
        }