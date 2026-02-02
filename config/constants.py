# --- API Configuration ---
PVA_PINS_BASE_URL = "https://api.pvapins.com/user/api/"

# --- Redis Key Prefixes ---
REDIS_PRICING_PREFIX = "pricing"
REDIS_PRICING_LOCK_PREFIX = "pricing_lock"
REDIS_SMS_LAST_ID_PREFIX = "sms_last"
REDIS_RATE_LIMIT_PREFIX = "rate_limit"

# --- Cache Durations (in seconds) ---
PRICE_CACHE_DURATION = 3600  # 1 hour (Prices might not change often)
PRICE_LOCK_DURATION = 900    # 15 minutes

# --- Payment Constants ---
DEFAULT_CURRENCY = "NGN"

# ==============================================================================
# LIVE SERVICE CONFIGURATION
# Your API does not support fetching lists of countries/services.
# You MUST configure them here. Prices will be fetched LIVE.
# ==============================================================================

# --- Available Countries ---
# 'id' and 'name' MUST EXACTLY match what the API expects for the 'country' parameter.
PVA_PINS_COUNTRIES = [
    {'id': 'Malaysia', 'name': '🇲🇾 Malaysia'},
    {'id': 'Indonesia', 'name': '🇮🇩 Indonesia'},
    {'id': 'USA', 'name': '🇺🇸 USA'},
    {'id': 'Philippines', 'name': '🇵🇭 Philippines'},
    {'id': 'Nigeria', 'name': '🇳🇬 Nigeria'},
    {'id': 'UK', 'name': '🇬🇧 UK'},
    # Add more countries here
]

# --- Available Services ---
# The 'id' must EXACTLY match the 'app' name the API expects.
PVA_PINS_SERVICES = [
    {'id': 'Google', 'name': 'Google / Gmail'},
    {'id': 'WhatsApp', 'name': 'WhatsApp'},
    {'id': 'Telegram', 'name': 'Telegram'},
    {'id': 'Facebook', 'name': 'Facebook'},
    {'id': 'Tiktok', 'name': 'Tiktok'},
    {'id': 'Amazon', 'name': 'Amazon'},
    # Add more services here
]

# --- Rental Pricing ---
# The API doesn't provide a way to get rent prices, so this must be configured.
# This is the base price in USD PER DAY for all rentals.
PVA_PINS_RENTAL_DAILY_RATE_USD = 0.50

# --- Temporary Number Duration ---
# The API does not provide duration info, so we configure a default here.
DEFAULT_TEMP_DURATION_MINUTES = 15
