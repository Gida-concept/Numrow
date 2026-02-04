import aiohttp
import json
import re
from typing import Optional, List, Dict

from config.settings import settings
from config.constants import PVA_PINS_BASE_URL, DEFAULT_TEMP_DURATION_MINUTES
from utils.logger import app_logger
from database.redis import redis_client

class PvaService:
    def __init__(self, api_key: str):
        if not api_key or "your_pva_service_api_key" in api_key:
            app_logger.warning("PVA_API_KEY is not set. Service will not function.")
        self.api_key = api_key

    async def _make_request(self, endpoint: str, params: dict = None, expect_json: bool = True) -> Optional[Dict]:
        url = f"{PVA_PINS_BASE_URL}{endpoint}"
        try:
            async with aiohttp.ClientSession() as session:
                if params and "customer" in params: params['customer'] = self.api_key
                async with session.get(url, params=params, timeout=30) as response:
                    response.raise_for_status()
                    if not expect_json:
                        text_response = await response.text()
                        app_logger.debug(f"PVA API Response (text) for {endpoint}: {text_response}")
                        return text_response
                    data = await response.json()
                    app_logger.debug(f"PVA API Response (json) for {endpoint}: {data}")
                    return data
        except Exception as e:
            app_logger.error(f"Failed API request to {endpoint}: {e}")
            return None

    async def get_countries(self, is_rent: bool = False) -> List[Dict]:
        cache_key = f"pva_countries:{'rent' if is_rent else 'temp'}"
        cached = await redis_client.get(cache_key)
        if cached: return json.loads(cached)
        params = {'is_rent': '1'} if is_rent else {}
        data = await self._make_request("load_countries.php", params)
        if data and isinstance(data, list):
            countries = [{'id': str(c['id']), 'name': c['full_name']} for c in data]
            await redis_client.set(cache_key, json.dumps(countries), ex=3600)
            return countries
        return []

    async def get_services(self, country_id: str, is_rent: bool = False) -> List[Dict]:
        cache_key = f"pva_services:{country_id}:{'rent' if is_rent else 'temp'}"
        cached = await redis_client.get(cache_key)
        if cached: return json.loads(cached)
        params = {'country_id': country_id}
        if is_rent: params['is_rent'] = '1'
        data = await self._make_request("load_apps.php", params)
        if data and isinstance(data, list):
            services = [{'id': str(s['id']), 'name': s['full_name'], 'cost_usd': float(s['deduct'])} for s in data if float(s.get('deduct', 0)) > 0]
            await redis_client.set(cache_key, json.dumps(services), ex=900)
            return services
        return []

    async def get_price_and_duration(self, service_id: str, country_id: str, is_rent: bool = False) -> Optional[dict]:
        services = await self.get_services(country_id, is_rent)
        for service in services:
            if service['id'] == service_id:
                if is_rent: duration_minutes = 3 * 24 * 60
                else: duration_minutes = DEFAULT_TEMP_DURATION_MINUTES
                return {'cost_usd': service['cost_usd'], 'duration_minutes': duration_minutes}
        return None

    async def buy_number(self, service_id: str, country_id: str, country_name: str, is_rent: bool = False) -> Optional[dict]:
        services = await self.get_services(country_id, is_rent)
        service_full_name = next((s['name'] for s in services if s['id'] == service_id), None)
        if not service_full_name: return None
        params = {'customer': self.api_key, 'app': service_full_name, 'country': country_name}
        endpoint = "rent.php" if is_rent else "get_number.php"
        url = f"{PVA_PINS_BASE_URL}{endpoint}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=30) as response:
                    response.raise_for_status()
                    raw_response_text = await response.text()
                    app_logger.info(f"RAW RESPONSE from {endpoint}: '{raw_response_text}'")
                    if is_rent:
                        try:
                            data = json.loads(raw_response_text)
                            if data.get('code') == 100:
                                phone_number = data.get('data', '')
                                sanitized_number = re.sub(r'[^\d+]', '', phone_number)
                                if sanitized_number: return {"activation_id": sanitized_number, "phone_number": sanitized_number}
                        except json.JSONDecodeError: return None
                    else:
                        cleaned_text = raw_response_text.strip()
                        match = re.search(r'\+?\d{10,}', cleaned_text)
                        if match: return {"activation_id": match.group(0), "phone_number": match.group(0)}
        except Exception as e:
            app_logger.error(f"Error during buy_number request: {e}")
        return None

    async def renew_rental_number(self, service_id: str, country_id: str, country_name: str, phone_number: str) -> bool:
        """LIVE: Renews a rental number."""
        services = await self.get_services(country_id, is_rent=True)
        service_full_name = next((s['name'] for s in services if s['id'] == service_id), None)
        if not service_full_name: return False
        params = {'customer': self.api_key, 'app': service_full_name, 'country': country_name, 'number': phone_number}
        data = await self._make_request("rent_renew_number.php", params, expect_json=True)
        if data and data.get('code') == 100:
            app_logger.info(f"Successfully renewed number {phone_number}.")
            return True
        app_logger.error(f"Failed to renew number {phone_number}. API Response: {data}")
        return False

    async def get_sms(self, phone_number: str, service_id: str, country_id: str, country_name: str, is_rent: bool = False) -> Optional[dict]:
        # ... (this function is correct and unchanged) ...
        services = await self.get_services(country_id, is_rent)
        service_full_name = next((s['name'] for s in services if s['id'] == service_id), None)
        if not service_full_name: return {"status": "ERROR"}
        params = {'customer': self.api_key, 'number': phone_number, 'app': service_full_name, 'country': country_name}
        endpoint = "load_rent_code.php" if is_rent else "get_sms.php"
        if not is_rent:
            response_text = await self._make_request(endpoint, params, expect_json=False)
            if not response_text or "you have not received any code yet" in response_text.lower(): return {"status": "WAITING"}
            return {"status": "OK", "code": response_text}
        response_json = await self._make_request(endpoint, params, expect_json=True)
        if response_json and isinstance(response_json, list) and len(response_json) > 0: return {"status": "OK", "code": response_json[0]['message']}
        return {"status": "WAITING"}

pva_service = PvaService(api_key=settings.PVA_API_KEY)
