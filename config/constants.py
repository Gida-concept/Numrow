# --- Redis Key Prefixes (as per blueprint) ---
# Used to organize data in Redis and prevent key collisions.
REDIS_PRICING_PREFIX = "pricing"
REDIS_PRICING_LOCK_PREFIX = "pricing_lock"
REDIS_SMS_LAST_ID_PREFIX = "sms_last"
REDIS_RATE_LIMIT_PREFIX = "rate_limit"

# --- Cache Durations (in seconds) ---
# How long the final NGN price for a service is cached.
# 3600 seconds = 1 hour
PRICE_CACHE_DURATION = 3600

# How long a price is "locked" for a user after they click "Pay".
# This prevents the price from changing mid-transaction.
# 900 seconds = 15 minutes
PRICE_LOCK_DURATION = 900

# --- Payment Constants ---
DEFAULT_CURRENCY = "NGN"

# --- PVA Service Constants ---
# Placeholder for the specific PVA service provider name/code.
# This might be 'opt25' for 5sim, or a different code for another provider.
PVA_OPERATOR_CODE = "any" # Or a specific operator if required

# Example status codes from a PVA service
PVA_SUCCESS_STATUS = "SUCCESS"
PVA_PENDING_STATUS = "PENDING"
PVA_CANCELED_STATUS = "CANCELED"
PVA_BANNED_STATUS = "BANNED"

# --- Pagination ---
DEFAULT_PAGE_SIZE = 10