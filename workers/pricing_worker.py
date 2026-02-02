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
    return Decimal("1550.75")

def _calculate_final_ngn(pva_usd_price: Decimal, fx_rate_to_use: Decimal) -> int:
    markup_multiplier = Decimal(1 + (settings.PRICE_MARKUP_PERCENTAGE / 100))
    final_usd = pva_usd_price * markup_multiplier
    final_ngn_unrounded = final_usd * fx_rate_to_use
    final_ngn_rounded = int(math.ceil(final_ngn_unrounded / 10)) * 10
    app_logger.info(f"Final NGN price: ₦{final_ngn_rounded} (from ${pva_usd_price:.4f} base)")
    return final_ngn_rounded

async def get_final_price(country_id: str, service_id: str, number_type: str, rent_days: Optional[int] = None) -> tuple[Optional[int], Optional[str], Optional[int]]:
    if number_type == 'rent' and not rent_days:
        raise ValueError("rent_days must be provided for rental pricing")

    rent_suffix = f":{rent_days}" if number_type == 'rent' else ""
    cache_key = f"{REDIS_PRICING_PREFIX}:{country_id}:{service_id}:{number_type}{rent_suffix}"
    
    cached_data = await redis_client.get(cache_key)
    if cached_data:
        data = json.loads(cached_data)
        app_logger.info(f"CACHE HIT for {cache_key}. Price: ₦{data['price']}, Duration: {data['duration_minutes']} mins")
        return data['price'], cache_key, data['duration_minutes']

    app_logger.info(f"CACHE MISS for {cache_key}. Calculating new price...")

    fx_rate = await _get_live_fx_rate()
    fx_rate_to_use = min(fx_rate, Decimal(settings.FX_RATE_CAP))
    
    pva_price_data = None
    duration_minutes = 0

    if number_type == 'temporary':
        pva_price_data = await pva_service.get_price_and_duration(service_id=service_id, country_name=country_id)
        if pva_price_data:
            duration_minutes = pva_price_data.get('duration_minutes', 0)
    
    elif number_type == 'rent':
        pva_price_data = await pva_service.get_rent_price(days=rent_days)
        if pva_price_data:
            duration_minutes = rent_days * 24 * 60

    if not pva_price_data or 'cost_usd' not in pva_price_data or pva_price_data['cost_usd'] <= 0:
        app_logger.error(f"Could not retrieve a valid, non-zero USD price for {cache_key}")
        return None, None, None
        
    pva_usd_price = Decimal(str(pva_price_data['cost_usd']))
    final_ngn = _calculate_final_ngn(pva_usd_price, fx_rate_to_use)
    
    if final_ngn <= 0:
        return None, None, None

    data_to_cache = {"price": final_ngn, "duration_minutes": duration_minutes}
    await redis_client.set(cache_key, json.dumps(data_to_cache), ex=PRICE_CACHE_DURATION)
    app_logger.info(f"Saved new price to cache: {data_to_cache}")
    
    return final_ngn, cache_key, duration_minutes
