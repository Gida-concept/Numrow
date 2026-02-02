import aiohttp
import json
from typing import Optional

from config.settings import settings
from config.constants import (
    PVA_PINS_BASE_URL,
    PVA_PINS_COUNTRIES,
    PVA_PINS_SERVICES,
    PVA_PINS_RENTAL_DAILY_RATE_USD,
    DEFAULT_TEMP_DURATION_MINUTES
)
from utils.logger import app_logger

class PvaService:
    def __init__(self, api_key: str):
        if not api_key or api_key == "your_pva_service_api_key":
            app_logger.warning("PVA_API_KEY is not set. Service will not work.")
        self.api_key = api_key

    async def _make_request(self, endpoint: str, params: dict) -> Optional[str]:
        """Helper to make requests to the PVA Pins API."""
        if not self.api_key:
            return "ERROR: API Key not configured."
            
        all_params = {'customer': self.api_key, **params}
        url = f"{PVA_PINS_BASE_URL}{endpoint}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=all_params, timeout=30) as response:
                    response.raise_for_status()
                    text_response = await response.text()
                    app_logger.debug(f"PVA Pins API Response for {endpoint}: {text_response}")
                    
                    if "not found" in text_response.lower() or "error" in text_response.lower():
                         app_logger.error(f"PVA Pins API Error: {text_response}")
                         return None
                    return text_response
        except Exception as e:
            app_logger.error(f"Failed to make request to PVA Pins API: {e}")
            return None

    # --- LISTS (from config) ---
    async def get_all_countries(self) -> list:
        return PVA_PINS_COUNTRIES

    async def get_all_services(self) -> list:
        return PVA_PINS_SERVICES

    # --- PRICING (partially live) ---
    async def get_price_and_duration(self, service_id: str, country_name: str) -> Optional[dict]:
        """
        LIVE: Fetches the price for a service in a country using get_rates.php.
        Duration is from config as API does not provide it.
        """
        params = {'country': country_name}
        response = await self._make_request("get_rates.php", params)
        
        if not response:
            return None
            
        try:
            # The response is a JSON array of objects
            rates_data = json.loads(response)
            
            # Find the specific service in the list (case-insensitive search)
            for service_rate in rates_data:
                if service_rate.get('app', '').lower() == service_id.lower():
                    cost_myr = float(service_rate.get('rates', 0))
                    # The API returns price in MYR. We need to convert it to USD to fit our system.
                    # This is an ESTIMATE. You should adjust this MYR_TO_USD rate.
                    MYR_TO_USD_RATE = 0.21  # Example: 1 MYR = 0.21 USD
                    cost_usd = cost_myr * MYR_TO_USD_RATE
                    
                    app_logger.info(f"Live price for {service_id} in {country_name}: {cost_myr} MYR -> ${cost_usd:.4f} USD")
                    
                    return {
                        'cost_usd': cost_usd,
                        'duration_minutes': DEFAULT_TEMP_DURATION_MINUTES
                    }
            
            app_logger.warning(f"Service '{service_id}' not found in rates for country '{country_name}'.")
            return None

        except (json.JSONDecodeError, TypeError, KeyError) as e:
            app_logger.error(f"Failed to parse get_rates.php response: {e}")
            return None

    async def get_rent_price(self, days: int) -> Optional[dict]:
        """Calculates rental price based on configured daily rate."""
        total_cost = PVA_PINS_RENTAL_DAILY_RATE_USD * days
        return {'cost_usd': total_cost}
        
    # --- LIVE API CALLS (Purchase & SMS) ---
    async def buy_number(self, service_id: str, country_name: str) -> Optional[dict]:
        """LIVE: Purchases a new temporary number."""
        params = {'app': service_id, 'country': country_name}
        response = await self._make_request("get_number.php", params)
        
        if response and response.strip().startswith('+'):
            phone_number = response.strip()
            return {"activation_id": phone_number, "phone_number": phone_number}
        return None

    async def get_sms(self, phone_number: str, service_id: str, country_name: str) -> Optional[dict]:
        """LIVE: Polls for an SMS for a given temporary number."""
        params = {'number': phone_number, 'app': service_id, 'country': country_name}
        response = await self._make_request("get_sms.php", params)
        
        if not response:
            return {"status": "ERROR"}
        if "you have not received any code yet" in response.lower():
            return {"status": "WAITING"}
        
        return {"status": "OK", "code": response}

pva_service = PvaService(api_key=settings.PVA_API_KEY)
