import asyncio
import math
from typing import Optional # <-- Added this missing import
from decimal import Decimal, ROUND_UP

from config.settings import settings
from config.constants import REDIS_PRICING_PREFIX, PRICE_CACHE_DURATION
from database.redis import redis_client
from services.pva_service import pva_service
from utils.logger import app_logger

async def _get_live_fx_rate() -> Decimal:
    """
    Fetches the live USD to NGN exchange rate.
    """
    app_logger.info("Fetching live FX rate (MOCK)...")
    await asyncio.sleep(0.1) # Simulate network latency
    mock_rate = Decimal("1550.75")
    app_logger.info(f"Live FX rate is ₦{mock_rate}/USD (MOCK)")
    return mock_rate

def _calculate_final_ngn(pva_usd_price: Decimal, fx_rate_to_use: Decimal) -> int:
    """
    Applies the core pricing logic: markup and conversion.
    """
    markup_multiplier = Decimal(1 + (settings.PRICE_MARKUP_PERCENTAGE / 100))
    
    final_usd = pva_usd_price * markup_multiplier
    app_logger.debug(f"Price after markup: ${final_usd:.4f}")
    
    # Calculate final NGN price
    final_ngn_unrounded = final_usd * fx_rate_to_use
    app_logger.debug(f"Unrounded NGN price: ₦{final_ngn_unrounded:.4f}")

    # Round up to the nearest 10 NGN
    final_ngn_rounded = int(math.ceil(final_ngn_unrounded / 10)) * 10
    app_logger.info(f"Final rounded NGN price: ₦{final_ngn_rounded}")
    
    return final_ngn_rounded

async def get_final_ngn_price(country_id: str, service_id: str, number_type: str) -> tuple[Optional[int], Optional[str]]:
    """
    The main public function for this worker. It gets the final price in NGN.
    """
    # 1. Check Cache
    cache_key = f"{REDIS_PRICING_PREFIX}:{country_id}:{service_id}:{number_type}"
    cached_price = await redis_client.get(cache_key)
    
    if cached_price:
        app_logger.info(f"CACHE HIT for {cache_key}. Price: ₦{cached_price}")
        return int(cached_price), cache_key

    app_logger.info(f"CACHE MISS for {cache_key}. Calculating new price...")

    # 2. Fetch Base Price from PVA Service
    pva_price_data = await pva_service.get_prices(country=country_id, service=service_id)
    if not pva_price_data or 'cost_usd' not in pva_price_data:
        app_logger.error(f"Could not retrieve USD price for {service_id} in country {country_id}")
        return None, None
        
    pva_usd_price = Decimal(str(pva_price_data['cost_usd']))
    app_logger.info(f"Fetched base PVA price: ${pva_usd_price:.4f}")

    # 3. Apply Pricing Engine Rules
    live_fx_rate = await _get_live_fx_rate()
    fx_rate_to_use = min(live_fx_rate, Decimal(settings.FX_RATE_CAP))
    app_logger.info(f"Using FX rate: ₦{fx_rate_to_use}/USD (capped at ₦{settings.FX_RATE_CAP})")

    final_ngn = _calculate_final_ngn(pva_usd_price, fx_rate_to_use)
    
    if final_ngn <= 0:
        app_logger.error("Calculated price is zero or negative. Aborting.")
        return None, None

    # 4. Store in Cache
    await redis_client.set(cache_key, final_ngn, ex=PRICE_CACHE_DURATION)
    app_logger.info(f"Saved new price to cache with TTL {PRICE_CACHE_DURATION}s.")
    
    return final_ngn, cache_key
