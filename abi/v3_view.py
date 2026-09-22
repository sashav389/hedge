V3_POOL_ABI = [
    {
        "inputs": [],
        "name": "slot0",
        "outputs": [
            {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
            {"internalType": "int24", "name": "tick", "type": "int24"},
            {"internalType": "uint16", "name": "observationIndex", "type": "uint16"},
            {"internalType": "uint16", "name": "observationCardinality", "type": "uint16"},
            {"internalType": "uint16", "name": "observationCardinalityNext", "type": "uint16"},
            {"internalType": "uint8", "name": "feeProtocol", "type": "uint8"},
            {"internalType": "bool", "name": "unlocked", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "liquidity",
        "outputs": [
            {"internalType": "uint128", "name": "", "type": "uint128"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "token0",
        "outputs": [
            {"internalType": "address", "name": "", "type": "address"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "token1",
        "outputs": [
            {"internalType": "address", "name": "", "type": "address"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "fee",
        "outputs": [
            {"internalType": "uint24", "name": "", "type": "uint24"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

V3_POSITION_MANAGER_ABI = [
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "tokenId",
                "type": "uint256"
            }
        ],
        "name": "positions",
        "outputs": [
            {
                "internalType": "uint96",
                "name": "nonce",
                "type": "uint96"
            },
            {
                "internalType": "address",
                "name": "operator",
                "type": "address"
            },
            {
                "internalType": "address",
                "name": "token0",
                "type": "address"
            },
            {
                "internalType": "address",
                "name": "token1",
                "type": "address"
            },
            {
                "internalType": "uint24",
                "name": "fee",
                "type": "uint24"
            },
            {
                "internalType": "int24",
                "name": "tickLower",
                "type": "int24"
            },
            {
                "internalType": "int24",
                "name": "tickUpper",
                "type": "int24"
            },
            {
                "internalType": "uint128",
                "name": "liquidity",
                "type": "uint128"
            },
            {
                "internalType": "uint256",
                "name": "feeGrowthInside0LastX128",
                "type": "uint256"
            },
            {
                "internalType": "uint256",
                "name": "feeGrowthInside1LastX128",
                "type": "uint256"
            },
            {
                "internalType": "uint128",
                "name": "tokensOwed0",
                "type": "uint128"
            },
            {
                "internalType": "uint128",
                "name": "tokensOwed1",
                "type": "uint128"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]
