import aiohttp
from typing import Optional

from config.settings import settings
from config.constants import (
    PVA_PINS_BASE_URL,
    PVA_PINS_COUNTRIES,
    PVA_PINS_SERVICES,
    PVA_PINS_PRICING,
    PVA_PINS_RENTAL_DAILY_RATE_USD
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
            
        # Add the API key to every request
        all_params = {'customer': self.api_key, **params}
        url = f"{PVA_PINS_BASE_URL}{endpoint}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=all_params, timeout=30) as response:
                    response.raise_for_status()
                    text_response = await response.text()
                    app_logger.debug(f"PVA Pins API Response for {endpoint}: {text_response}")
                    
                    # Check for common error strings in the response
                    if "not found" in text_response.lower() or "error" in text_response.lower():
                         app_logger.error(f"PVA Pins API Error: {text_response}")
                         return None
                    return text_response
        except Exception as e:
            app_logger.error(f"Failed to make request to PVA Pins API: {e}")
            return None

    # --- LISTS AND PRICING (from config/constants.py) ---
    async def get_all_countries(self) -> list:
        return PVA_PINS_COUNTRIES

    async def get_all_services(self) -> list:
        return PVA_PINS_SERVICES

    async def get_price_and_duration(self, service_id: str) -> Optional[dict]:
        """Gets configured price and duration for a service."""
        pricing = PVA_PINS_PRICING.get(service_id, PVA_PINS_PRICING['default'])
        return pricing

    async def get_rent_price(self, days: int) -> Optional[dict]:
        """Calculates rental price based on configured daily rate."""
        total_cost = PVA_PINS_RENTAL_DAILY_RATE_USD * days
        return {'cost_usd': total_cost}
        
    # --- LIVE API CALLS ---
    async def buy_number(self, service_id: str, country_name: str) -> Optional[dict]:
        """LIVE: Purchases a new temporary number."""
        params = {'app': service_id, 'country': country_name}
        response = await self._make_request("get_number.php", params)
        
        # The API docs don't specify success format. We assume it returns just the number.
        if response and response.strip().startswith('+'): # A simple check for a phone number
            phone_number = response.strip()
            # For this API, the number itself acts as the activation ID
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
        
        # Assume any other successful response is the SMS code/text
        return {"status": "OK", "code": response}

pva_service = PvaService(api_key=settings.PVA_API_KEY)
