from math import isqrt


Q96 = 2 ** 96


def tick_to_sqrt_price_x96(tick):
    """
    Преобразует tick Uniswap V3 в sqrtPriceX96.

    Используется целочисленная арифметика,
    аналогичная TickMath.getSqrtRatioAtTick().
    """

    abs_tick = abs(tick)

    ratio = 0x100000000000000000000000000000000

    if abs_tick & 0x1:
        ratio = (ratio * 0xfffcb933bd6fad37aa2d162d1a594001) >> 128
    if abs_tick & 0x2:
        ratio = (ratio * 0xfff97272373d413259a46990580e213a) >> 128
    if abs_tick & 0x4:
        ratio = (ratio * 0xfff2e50f5f656932ef12357cf3c7fdcc) >> 128
    if abs_tick & 0x8:
        ratio = (ratio * 0xffe5caca7e10e4e61c3624eaa0941cd0) >> 128
    if abs_tick & 0x10:
        ratio = (ratio * 0xffcb9843d60f6159c9db58835c926644) >> 128
    if abs_tick & 0x20:
        ratio = (ratio * 0xff973b41fa98c081472e6896dfb254c0) >> 128
    if abs_tick & 0x40:
        ratio = (ratio * 0xff2ea16466c96a3843ec78b326b52861) >> 128
    if abs_tick & 0x80:
        ratio = (ratio * 0xfe5dee046a99a2a811c461f1969c3053) >> 128
    if abs_tick & 0x100:
        ratio = (ratio * 0xfcbe86c7900a88aedcffc83b479aa3a4) >> 128
    if abs_tick & 0x200:
        ratio = (ratio * 0xf987a7253ac413176f2b074cf7815e54) >> 128
    if abs_tick & 0x400:
        ratio = (ratio * 0xf3392b0822b70005940c7a398e4b70f3) >> 128
    if abs_tick & 0x800:
        ratio = (ratio * 0xe7159475a2c29b7443b29c7fa6e889d9) >> 128
    if abs_tick & 0x1000:
        ratio = (ratio * 0xd097f3bdfd2022b8845ad8f792aa5825) >> 128
    if abs_tick & 0x2000:
        ratio = (ratio * 0xa9f746462d870fdf8a65dc1f90e061e5) >> 128
    if abs_tick & 0x4000:
        ratio = (ratio * 0x70d869a156d2a1b890bb3df62baf32f7) >> 128
    if abs_tick & 0x8000:
        ratio = (ratio * 0x31be135f97d08fd981231505542fcfa6) >> 128
    if abs_tick & 0x10000:
        ratio = (ratio * 0x9aa508b5b7a84e1c677de54f3e99bc9) >> 128
    if abs_tick & 0x20000:
        ratio = (ratio * 0x5d6af8dedb81196699c329225ee604) >> 128
    if abs_tick & 0x40000:
        ratio = (ratio * 0x2216e584f5fa1ea926041bedfe98) >> 128
    if abs_tick & 0x80000:
        ratio = (ratio * 0x48a170391f7dc42444e8fa2) >> 128

    if tick > 0:
        ratio = ((1 << 256) - 1) // ratio

    # Equivalent to TickMath:
    # uint160((ratio >> 32) + (ratio % 2**32 == 0 ? 0 : 1))
    sqrt_price_x96 = (ratio >> 32) + (1 if ratio & ((1 << 32) - 1) else 0)

    return sqrt_price_x96


def get_amount0(liquidity, sqrt_price_a, sqrt_price_b):
    """
    Количество token0 для диапазона.
    """

    if sqrt_price_a > sqrt_price_b:
        sqrt_price_a, sqrt_price_b = sqrt_price_b, sqrt_price_a

    return (
        liquidity
        * Q96
        * (sqrt_price_b - sqrt_price_a)
        // sqrt_price_b
        // sqrt_price_a
    )


def get_amount1(liquidity, sqrt_price_a, sqrt_price_b):
    """
    Количество token1 для диапазона.
    """

    if sqrt_price_a > sqrt_price_b:
        sqrt_price_a, sqrt_price_b = sqrt_price_b, sqrt_price_a

    return (
        liquidity
        * (sqrt_price_b - sqrt_price_a)
        // Q96
    )


def get_amounts(
    liquidity,
    sqrt_price_x96,
    tick_lower,
    tick_upper
):
    """
    Рассчитывает фактическое количество token0/token1
    внутри V3 LP позиции.
    """

    sqrt_price_lower = tick_to_sqrt_price_x96(tick_lower)
    sqrt_price_upper = tick_to_sqrt_price_x96(tick_upper)

    # Цена ниже диапазона
    if sqrt_price_x96 <= sqrt_price_lower:

        amount0 = get_amount0(
            liquidity,
            sqrt_price_lower,
            sqrt_price_upper
        )

        amount1 = 0

    # Цена выше диапазона
    elif sqrt_price_x96 >= sqrt_price_upper:

        amount0 = 0

        amount1 = get_amount1(
            liquidity,
            sqrt_price_lower,
            sqrt_price_upper
        )

    # Цена внутри диапазона
    else:

        amount0 = get_amount0(
            liquidity,
            sqrt_price_x96,
            sqrt_price_upper
        )

        amount1 = get_amount1(
            liquidity,
            sqrt_price_lower,
            sqrt_price_x96
        )

    return amount0, amount1


def format_amount(amount, decimals=18):
    """
    Перевод raw token amount в нормальные единицы.
    """

    return amount / (10 ** decimals)