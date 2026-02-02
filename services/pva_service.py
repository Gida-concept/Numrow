import asyncio
import aiohttp
from typing import Optional, Any

from config.settings import settings
from utils.logger import app_logger

# NOTE: These are example parameters and endpoints.
# You MUST replace them with the actual values from your PVA provider's API documentation.
PVA_BASE_URL = "https://api.pva-provider.com/stubs/handler_api.php"


class PvaService:
    """
    A service class to interact with the PVA provider's API.
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("PVA API key is required.")
        self.api_key = api_key
        # Common parameters for all requests
        self.base_params = {"api_key": self.api_key}

    async def _make_request(self, params: dict) -> Optional[Any]:
        """
        A private helper method to make asynchronous HTTP GET requests.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(PVA_BASE_URL, params={**self.base_params, **params}) as response:
                    response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

                    # PVA APIs often return plain text, not JSON. We need to handle this.
                    # Example responses: "ACCESS_NUMBER:ID:NUMBER" or "ERROR_NO_NUMBERS"
                    text_response = await response.text()
                    app_logger.debug(f"PVA API response: {text_response}")
                    return text_response

        except aiohttp.ClientError as e:
            app_logger.error(f"PVA API request failed: {e}")
            return None
        except Exception as e:
            app_logger.error(f"An unexpected error occurred during PVA API request: {e}")
            return None

    async def get_balance(self) -> Optional[float]:
        """
        Fetches the current account balance in USD.
        Example action: getBalance
        """
        params = {"action": "getBalance"}
        response = await self._make_request(params)
        # Example response: "ACCESS_BALANCE:123.45"
        if response and response.startswith("ACCESS_BALANCE:"):
            return float(response.split(':')[1])
        return None

    async def get_prices(self, country: str = "0", service: Optional[str] = None) -> Optional[dict]:
        """
        Fetches the prices for services in a specific country.
        This is what the Pricing Worker will use to get the base USD price.
        Example action: getPrices
        """
        params = {"action": "getPrices", "country": country}
        if service:
            params["service"] = service

        # This is a placeholder; many APIs don't support this directly and you must
        # query per service, or they provide a giant list.
        # For our blueprint, we only need the price for ONE service at a time.
        # Let's assume the API can give us the price for a specific service.
        app_logger.info(f"Fetching PVA price for service '{service}' in country '{country}'.")

        # --- MOCK IMPLEMENTATION ---
        # Replace this with a real API call.
        await asyncio.sleep(0.5)  # Simulate network latency
        # This mock returns a USD price based on the service ID.
        if service == 'wa':
            return {'cost_usd': 0.55}
        elif service == 'tg':
            return {'cost_usd': 0.30}
        else:
            return {'cost_usd': 0.25}
        # --- END MOCK ---

    async def buy_number(self, service: str, country: str) -> Optional[dict]:
        """
        Purchases a new phone number.
        Example action: getNumber
        """
        params = {"action": "getNumber", "service": service, "country": country}
        response = await self._make_request(params)
        # Example response: "ACCESS_NUMBER:ACTIVATION_ID:PHONE_NUMBER"
        if response and response.startswith("ACCESS_NUMBER:"):
            parts = response.split(':')
            return {"activation_id": parts[1], "phone_number": parts[2]}
        app_logger.warning(f"Failed to buy number. Response: {response}")
        return None

    async def get_sms(self, activation_id: str) -> Optional[dict]:
        """
        Polls for an SMS for a given activation.
        Example action: getStatus
        """
        params = {"action": "getStatus", "id": activation_id}
        response = await self._make_request(params)
        # Example success response: "STATUS_OK:SMS_CODE" or "STATUS_OK:FULL_SMS_TEXT"
        if response and response.startswith("STATUS_OK:"):
            return {"status": "OK", "code": response.split(':')[1]}
        # Example waiting response: "STATUS_WAIT_CODE"
        elif response == "STATUS_WAIT_CODE":
            return {"status": "WAITING"}
        return {"status": "ERROR", "details": response}


# A single, reusable instance of the service
pva_service = PvaService(api_key=settings.PVA_API_KEY)