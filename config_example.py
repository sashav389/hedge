# ==========================================
# RPC / WEBSOCKET ЭНДПОИНТЫ
# ==========================================
# Возьмите свои ключи в дашборде Alchemy (или другого RPC-провайдера)
# для каждой сети отдельно.

RPC_ROBIN = "https://robinhood-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_API_KEY"
RPC_BSC = "https://bnb-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_API_KEY"
WSS_ROBIN = "wss://robinhood-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_API_KEY"
WSS_BSC = "wss://bnb-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_API_KEY"
RPC_AVAX = "https://avax-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_API_KEY"
WSS_AVAX = "wss://avax-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_API_KEY"

CHAIN_ID = 4663  # Robinhood Chain

# ==========================================
# КЛЮЧИ БИРЖ / КОШЕЛЬКОВ - СЕКРЕТНО, НЕ КОММИТИТЬ
# ==========================================

HYPERLIQUID_ADDRESS = "YOUR_WALLET_ADDRESS"
HYPERLIQUID_PRIVATE_KEY = "YOUR_PRIVATE_KEY"

ASTER_USER = "YOUR_ASTER_USER_ADDRESS"
ASTER_SIGNER = "YOUR_ASTER_SIGNER_ADDRESS"
ASTER_PRIVATE_KEY = "YOUR_PRIVATE_KEY"

BINANCE_API = "YOUR_BINANCE_API_KEY"
BINANCE_SECRET = "YOUR_BINANCE_API_SECRET"

# ВАЖНО: не забудьте про BingX - в exchanges/bingx.py используются
# api_key/api_secret, передайте их сюда же, если ещё не добавили:
# BINGX_API_KEY = "YOUR_BINGX_API_KEY"
# BINGX_API_SECRET = "YOUR_BINGX_API_SECRET"

# ==========================================
# РЕЖИМ ТОРГОВЛИ
# ==========================================

LIVE_TRADING = False  # True только когда полностью уверены, начинайте с False

# ==========================================
# UNISWAP V4 - PoolManager / PositionManager (Robinhood Chain)
# ==========================================
# Это НЕ секреты - публичные адреса контрактов, безопасно коммитить как есть.

POOL_MANAGER = "0x8366A39CC670b4001A1121B8f6A443A643E40951"
POSITION_MANAGER = "0x58DAeC3116AAE6D93017bAAea7749052E8A04FA7"
V4_POOL_MANAGER = "0x8366a39CC670B4001A1121B8F6A443A643e40951"
V4_POSITION_MANAGER = "0x58daec3116aae6d93017baaea7749052e8a04fa7"

# ==========================================
# UNISWAP V3 - ПУЛЫ ПО СЕТЯМ
# ==========================================
# Тоже публичные адреса, не секреты.

V3_POOL_CASHCAT = "0xA70fc67C9F69da90B63a0e4C05D229954574E313"  # Robinhood Chain

# --- BSC ---
V3_POSITION_MANAGER_BSC = "0x7b8A01B39D58278b5DE7e48c8449c9f4F5170613"
V3_POOL_BLUAI = "0xe2183220b6725b2A1396878636b407C8dB0f42Ab"
V3_POOL_AKE = "0x20C0555Ea3e2066673416423a17D64275FA43488"
V3_POOL_AKE2 = "0x83FCd80D7973Cca1aA821590bBec66D27A2d4AD4"
STATE_VIEW = "0xF3334192d15450CDD385C8B70E03f9A6BD9e673B"

# --- AVAX ---
V3_POSITION_MANAGER_AVAX = "0x655C406EBFa14EE2006250925e54ec43AD184f8B"
V3_POOL_NXPC = "0x075B6f68B05fe21205f8827323A6F9b747B09e93"

# --- Robinhood Chain ---
V3_POSITION_MANAGER_ROBIN = "0x73991a25C818Bf1f1128dEAaB1492D45638DE0D3"

# ==========================================
# ПРОЧЕЕ
# ==========================================

BOOK_TICKER_ENDPOINT = "/fapi/v1/ticker/bookTicker"

POOL_ID = "0x1252fbfc4f6530a025ca351494245797b2a147b7b5d2dc8af7893e4e1a2e9df3"