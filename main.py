import asyncio
import csv
from datetime import datetime, timezone
import json

import websockets
from web3 import Web3

from config import (
    # BSC
    V3_POOL_AKE,
    RPC_BSC,
    WSS_BSC,

    # AVAX
    V3_POOL_NXPC,
    RPC_AVAX,
    WSS_AVAX,

    # Binance
    BINANCE_API,
    BINANCE_SECRET,

    # Aster
    ASTER_USER,
    ASTER_SIGNER,
    ASTER_PRIVATE_KEY,

    # Position managers
    V3_POSITION_MANAGER_BSC,
    V3_POSITION_MANAGER_AVAX, V3_POOL_AKE2,
)
from exchanges import binance

from exchanges.aster import Aster
from exchanges.binance import Binance

from hedge import Hedge

from rpc import RPC

from uniswap.positions import V3Position
from uniswap.v3_math import get_amounts, format_amount

from v3_pool import V3Pool


# ============================================================
# SWAP EVENT
# ============================================================

SWAP_EVENT_TOPIC = Web3.to_hex(
    Web3.keccak(
        text="Swap(address,address,int256,int256,uint160,uint128,int24)"
    )
)


# ============================================================
# НАСТРОЙКИ ПУЛОВ
# ============================================================

POOLS = [

    # ========================================================
    # BSC
    # ========================================================

    {
        "name": "AKE BSC",

        "token_id": 2642830,

        "pool": V3_POOL_AKE,

        "rpc": RPC_BSC,
        "wss": WSS_BSC,

        "symbol": "AKEUSDT",

        "exchange": "binance",

        "position_manager": V3_POSITION_MANAGER_BSC,
    },


    # ========================================================
    # AVAX
    # ========================================================

    {
        "name": "AKE ASTER",

        "token_id": 2642888,       # <-- поставь реальный Token ID

        "pool": V3_POOL_AKE2,

        "rpc": RPC_BSC,
        "wss": WSS_BSC,

        "symbol": "AKEUSDT",

        "exchange": "aster",

        "position_manager": V3_POSITION_MANAGER_BSC,
    },

]


# ============================================================
# WATCH ONE POOL
# ============================================================

async def watch_pool(config):

    name = config["name"]
    token_id = config["token_id"]

    pool_address = config["pool"]

    rpc_url = config["rpc"]
    wss_url = config["wss"]

    symbol = config["symbol"]

    exchange_name = config["exchange"]

    position_manager = config["position_manager"]


    print()
    print("=" * 70)
    print(f"START POOL: {name}")
    print(f"POOL:       {pool_address}")
    print(f"TOKEN ID:   {token_id}")
    print(f"SYMBOL:     {symbol}")
    print(f"RPC:        {rpc_url}")
    print(f"WSS:        {wss_url}")
    print(f"MANAGER:    {position_manager}")
    print("=" * 70)


    # ========================================================
    # RPC
    # ========================================================

    rpc = RPC(rpc_url)


    # ========================================================
    # POOL
    # ========================================================

    pool = V3Pool(
        rpc,
        pool_address
    )


    # ========================================================
    # POSITION
    # ========================================================

    position = V3Position(
        rpc,
        position_manager
    )


    # ========================================================
    # EXCHANGE
    # ========================================================

    if exchange_name == "binance":

        exchange = Binance(
            BINANCE_API,
            BINANCE_SECRET
        )

    elif exchange_name == "aster":

        exchange = Aster(
            ASTER_USER,
            ASTER_SIGNER,
            ASTER_PRIVATE_KEY
        )

    else:

        raise ValueError(
            f"Unknown exchange: {exchange_name}"
        )


    # ========================================================
    # HEDGE
    # ========================================================

    hedge = Hedge(
        exchange,
        symbol
    )


    # ========================================================
    # POSITION CACHE
    # ========================================================

    position_cache = {}


    def refresh_position():

        position_info = position.get_position(
            token_id
        )

        position_cache["liquidity"] = (
            position_info["liquidity"]
        )

        position_cache["tick_lower"] = (
            position_info["tickLower"]
        )

        position_cache["tick_upper"] = (
            position_info["tickUpper"]
        )

        position_cache["token0"] = (
            position_info["token0"]
        )

        position_cache["token1"] = (
            position_info["token1"]
        )


        print()
        print(f"[{name}] POSITION UPDATED")

        print(
            "Liquidity:",
            position_cache["liquidity"]
        )

        print(
            "Range:",
            position_cache["tick_lower"],
            "→",
            position_cache["tick_upper"]
        )

        print(
            "TOKEN0:",
            position_cache["token0"]
        )

        print(
            "TOKEN1:",
            position_cache["token1"]
        )


    # ========================================================
    # INITIAL POSITION
    # ========================================================

    refresh_position()


    # ========================================================
    # PRICE UPDATE
    # ========================================================

    def process_price_update(
        sqrt_price_x96,
        current_tick
    ):

        try:

            amount0_raw, amount1_raw = get_amounts(

                position_cache["liquidity"],

                sqrt_price_x96,

                position_cache["tick_lower"],

                position_cache["tick_upper"],
            )


            amount0 = format_amount(
                amount0_raw,
                18
            )

            amount1 = format_amount(
                amount1_raw,
                18
            )


            print()
            print("=" * 70)

            print(
                f"[{name}] SWAP"
            )

            print(
                "Current tick:",
                current_tick
            )

            print(
                "sqrtPriceX96:",
                sqrt_price_x96
            )


            print()
            print("=== TOKENS IN LP ===")

            print(
                "TOKEN0:",
                position_cache["token0"]
            )

            print(
                "Amount0:",
                amount0
            )

            print(
                "TOKEN1:",
                position_cache["token1"]
            )

            print(
                "Amount1:",
                amount1
            )


            # =================================================
            # HEDGE
            # =================================================

            hedge_result = hedge.rebalance(
                amount0
            )


            print()
            print("=== HEDGE ===")

            print(
                "LP:",
                hedge_result["lp_amount"]
            )

            print(
                "CURRENT SHORT:",
                hedge_result["current_short"]
            )

            print(
                "TARGET SHORT:",
                hedge_result["target_short"]
            )

            print(
                "DELTA:",
                hedge_result["delta"]
            )

            print(
                "DEVIATION:",
                hedge_result["deviation"] * 100,
                "%"
            )

            print(
                "ACTION:",
                hedge_result["action"]
            )

            print(
                "AMOUNT:",
                hedge_result["amount"]
            )

            print("=" * 70)


        except Exception as e:

            print()
            print(
                f"[{name}] ERROR "
                f"in process_price_update:"
            )

            print(e)


    # ========================================================
    # WEBSOCKET SUBSCRIPTION
    # ========================================================

    subscribe_payload = {

        "jsonrpc": "2.0",

        "id": 1,

        "method": "eth_subscribe",

        "params": [

            "logs",

            {
                "address": pool_address,

                "topics": [
                    SWAP_EVENT_TOPIC
                ],
            },

        ],
    }


    # ========================================================
    # WEBSOCKET LOOP
    # ========================================================

    while True:

        try:

            print(
                f"[{name}] Connecting WSS..."
            )


            async with websockets.connect(
                wss_url
            ) as ws:


                await ws.send(
                    json.dumps(
                        subscribe_payload
                    )
                )


                confirmation = await ws.recv()


                print(
                    f"[{name}] SUBSCRIBED:",
                    confirmation
                )


                # =================================================
                # EVENTS
                # =================================================

                async for message in ws:

                    data = json.loads(
                        message
                    )


                    if "params" not in data:
                        continue


                    log = data[
                        "params"
                    ][
                        "result"
                    ]


                    raw = log[
                        "data"
                    ][
                        2:
                    ]


                    # =================================================
                    # SWAP EVENT DATA
                    #
                    # amount0       0:64
                    # amount1      64:128
                    # sqrtPrice   128:192
                    # liquidity   192:256
                    # tick        256:320
                    # =================================================

                    sqrt_price_x96 = int(
                        raw[128:192],
                        16
                    )


                    tick_raw = int(
                        raw[256:320],
                        16
                    )


                    current_tick = (

                        tick_raw - (1 << 24)

                        if tick_raw >= (1 << 23)

                        else tick_raw
                    )


                    # =================================================
                    # PROCESS
                    # =================================================

                    await asyncio.get_event_loop().run_in_executor(

                        None,

                        process_price_update,

                        sqrt_price_x96,

                        current_tick,
                    )


        except Exception as e:

            print()

            print(
                f"[{name}] WebSocket error:"
            )

            print(e)

            print(
                f"[{name}] reconnect in 3 sec..."
            )


            await asyncio.sleep(3)


# ============================================================
# MAIN
# ============================================================

async def main():

    await asyncio.gather(

        watch_pool(
            POOLS[0]
        ),

        watch_pool(
            POOLS[1]
        ),

    )



if __name__ == "__main__":

    print(
        "SWAP TOPIC:",
        SWAP_EVENT_TOPIC
    )

    print(
        "TOPIC LENGTH:",
        len(SWAP_EVENT_TOPIC) - 2
    )

    asyncio.run(
        main()
    )