import asyncio
import math
import json
from typing import Optional
from decimal import Decimal, ROUND_UP

from config.settings import settings
from config.constants import REDIS_PRICING_PREFIX, PRICE_CACHE_DURATION
from database.redis import redis_client
from services.pva_service import pva_service
from utils.logger import app_logger

async def _get_live_fx_rate() -> Decimal:
    await asyncio.sleep(0.1)
    return Decimal("1600.00") # Use the cap as the rate for stability

def _calculate_final_ngn(cost_usd: Decimal, fx_rate_to_use: Decimal) -> int:
    markup_multiplier = Decimal(1 + (settings.PRICE_MARKUP_PERCENTAGE / 100))
    final_usd = cost_usd * markup_multiplier
    final_ngn_unrounded = final_usd * fx_rate_to_use
    final_ngn_rounded = int(math.ceil(final_ngn_unrounded / 10)) * 10
    app_logger.info(f"Final NGN price: ₦{final_ngn_rounded} (from ${cost_usd:.4f} base)")
    return final_n_rounded

async def get_final_price(country_id: str, service_id: str, is_rent: bool) -> tuple[Optional[int], Optional[str], Optional[int]]:
    """
    Gets the final price in NGN by fetching the live USD price,
    applying markup, and converting to NGN.
    """
    cache_key = f"{REDIS_PRICING_PREFIX}:{country_id}:{service_id}:{'rent' if is_rent else 'temp'}"
    cached_data = await redis_client.get(cache_key)
    if cached_data:
        data = json.loads(cached_data)
        app_logger.info(f"CACHE HIT for {cache_key}: ₦{data['price']}")
        return data['price'], cache_key, data['duration']

    app_logger.info(f"CACHE MISS for {cache_key}. Calculating new price...")

    price_data = await pva_service.get_price_and_duration(service_id=service_id, country_id=country_id, is_rent=is_rent)

    if not price_data or 'cost_usd' not in price_data or price_data['cost_usd'] <= 0:
        app_logger.error(f"Could not retrieve a valid, non-zero USD price for {cache_key}")
        return None, None, None
        
    cost_usd = Decimal(str(price_data['cost_usd']))
    duration_minutes = price_data.get('duration_minutes', 0)

    fx_rate = await _get_live_fx_rate()
    fx_rate_to_use = min(fx_rate, Decimal(settings.FX_RATE_CAP))
    
    final_ngn = _calculate_final_ngn(cost_usd, fx_rate_to_use)
    
    if final_ngn <= 0:
        return None, None, None

    data_to_cache = {"price": final_ngn, "duration": duration_minutes}
    await redis_client.set(cache_key, json.dumps(data_to_cache), ex=PRICE_CACHE_DURATION)
    app_logger.info(f"Saved new price to cache: {data_to_cache}")
    
    return final_ngn, cache_key, duration_minutes
