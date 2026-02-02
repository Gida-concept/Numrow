import aiohttp
import json
from typing import Optional, List, Dict

from config.settings import settings
from config.constants import PVA_PINS_BASE_URL, DEFAULT_TEMP_DURATION_MINUTES
from utils.logger import app_logger
from database.redis import redis_client

class PvaService:
    def __init__(self, api_key: str):
        if not api_key or "your_pva_service_api_key" in api_key:
            app_logger.warning("PVA_API_KEY is not set. The service will not function.")
        self.api_key = api_key

    async def _make_request(self, endpoint: str, params: dict = None) -> Optional[Dict]:
        """Helper to make requests and parse JSON response."""
        url = f"{PVA_PINS_BASE_URL}{endpoint}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=30) as response:
                    response.raise_for_status()
                    data = await response.json()
                    app_logger.debug(f"PVA Pins API Response for {endpoint}: {data}")
                    return data
        except Exception as e:
            app_logger.error(f"Failed API request to {endpoint}: {e}")
            return None
            
    # --- LIVE LISTS & PRICING ---

    async def get_countries(self, is_rent: bool = False) -> List[Dict]:
        """LIVE: Fetches all available countries from the API and caches them."""
        cache_key = f"pva_countries:{'rent' if is_rent else 'temp'}"
        cached = await redis_client.get(cache_key)
        if cached:
            app_logger.info(f"Loaded countries from cache (rent={is_rent})")
            return json.loads(cached)

        app_logger.info(f"Fetching live countries from API (rent={is_rent})")
        params = {'is_rent': '1'} if is_rent else {}
        data = await self._make_request("load_countries.php", params)
        
        if data and isinstance(data, list):
            # The API uses 'full_name' for the name and 'id' for the ID. We map this.
            countries = [{'id': str(c['id']), 'name': c['full_name']} for c in data]
            await redis_client.set(cache_key, json.dumps(countries), ex=3600) # Cache for 1 hour
            return countries
        return []

    async def get_services(self, country_id: str, is_rent: bool = False) -> List[Dict]:
        """LIVE: Fetches all available services for a country from the API and caches them."""
        cache_key = f"pva_services:{country_id}:{'rent' if is_rent else 'temp'}"
        cached = await redis_client.get(cache_key)
        if cached:
            app_logger.info(f"Loaded services for {country_id} from cache (rent={is_rent})")
            return json.loads(cached)

        app_logger.info(f"Fetching live services for {country_id} from API (rent={is_rent})")
        params = {'country_id': country_id}
        if is_rent:
            params['is_rent'] = '1'
        
        data = await self._make_request("load_apps.php", params)
        
        if data and isinstance(data, list):
            # The API uses 'full_name' for the app's real name and 'deduct' for the price
            services = [{'id': s['full_name'], 'name': s['full_name'], 'cost_usd': float(s['deduct'])} for s in data if float(s.get('deduct', 0)) > 0]
            await redis_client.set(cache_key, json.dumps(services), ex=900) # Cache for 15 minutes
            return services
        return []

    async def get_price_and_duration(self, service_id: str, country_id: str, is_rent: bool = False) -> Optional[dict]:
        """Gets price and duration for a specific service by re-fetching the service list."""
        services = await self.get_services(country_id, is_rent)
        for service in services:
            if service['id'] == service_id:
                # The API doesn't give duration for temp numbers, so we use a default.
                # For rent, the duration is fixed by the provider.
                duration = DEFAULT_TEMP_DURATION_MINUTES # Default for both for now
                return {'cost_usd': service['cost_usd'], 'duration_minutes': duration}
        return None

    # --- LIVE ACTIONS (BUYING & SMS) ---
    async def buy_number(self, service_id: str, country_name: str, is_rent: bool = False) -> Optional[dict]:
        """LIVE: Purchases a new number."""
        params = {'customer': self.api_key, 'app': service_id, 'country': country_name}
        endpoint = "rent.php" if is_rent else "get_number.php"
        
        data = await self._make_request(endpoint, params)
        
        if is_rent: # Rental API has a different response format
            if data and data.get('code') == 100:
                phone_number = data['data']
                return {"activation_id": phone_number, "phone_number": phone_number}
        else: # Temporary number API
             if data and isinstance(data, str) and data.strip().startswith('+'):
                phone_number = data.strip()
                return {"activation_id": phone_number, "phone_number": phone_number}
        return None

    async def get_sms(self, phone_number: str, service_id: str, country_name: str, is_rent: bool = False) -> Optional[dict]:
        """LIVE: Polls for an SMS."""
        params = {'customer': self.api_key, 'number': phone_number, 'app': service_id, 'country': country_name}
        endpoint = "load_rent_code.php" if is_rent else "get_sms.php"
        
        response = await self._make_request(endpoint, params)
        
        if is_rent:
            if response and isinstance(response, list) and len(response) > 0:
                # Return the latest message
                return {"status": "OK", "code": response[0]['message']}
            return {"status": "WAITING"}
        else: # Temporary number
            if not response or "you have not received any code yet" in str(response).lower():
                return {"status": "WAITING"}
            return {"status": "OK", "code": str(response)}

pva_service = PvaService(api_key=settings.PVA_API_KEY)
