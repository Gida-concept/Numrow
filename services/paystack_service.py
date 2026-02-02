import aiohttp
from typing import Optional, Tuple

from config.settings import settings
from utils.logger import app_logger
from config.constants import DEFAULT_CURRENCY

PAYSTACK_BASE_URL = "https://api.paystack.co"


class PaystackService:
    """
    A service class to interact with the Paystack API.
    """

    def __init__(self, secret_key: str):
        if not secret_key:
            raise ValueError("Paystack secret key is required.")
        self._secret_key = secret_key
        self._headers = {
            "Authorization": f"Bearer {self._secret_key}",
            "Content-Type": "application/json",
        }

    async def _make_request(
            self, method: str, endpoint: str, **kwargs
    ) -> Optional[dict]:
        """A private helper method for making API requests."""
        url = f"{PAYSTACK_BASE_URL}{endpoint}"
        try:
            async with aiohttp.ClientSession(headers=self._headers) as session:
                async with session.request(method, url, **kwargs) as response:
                    response_data = await response.json()
                    app_logger.debug(f"Paystack API Response ({response.status}): {response_data}")

                    if response.status >= 400:
                        app_logger.error(f"Paystack API error: {response_data.get('message')}")
                        return None

                    return response_data
        except aiohttp.ClientError as e:
            app_logger.error(f"Paystack request failed: {e}")
            return None

    async def initialize_transaction(
            self, email: str, amount_kobo: int, reference: str
    ) -> Optional[str]:
        """
        Initializes a transaction and returns the payment URL.

        :param email: Customer's email address.
        :param amount_kobo: The amount in the smallest currency unit (kobo).
        :param reference: A unique reference for the transaction.
        :return: The authorization URL for the user to complete payment.
        """
        payload = {
            "email": email,
            "amount": amount_kobo,
            "reference": reference,
            "currency": DEFAULT_CURRENCY,
        }
        app_logger.info(f"Initializing Paystack transaction for ref: {reference}")
        response = await self._make_request("POST", "/transaction/initialize", json=payload)

        if response and response.get("status"):
            return response.get("data", {}).get("authorization_url")
        return None

    async def verify_transaction(self, reference: str) -> Optional[Tuple[str, int]]:
        """
        Verifies the status of a transaction.

        :param reference: The transaction reference to verify.
        :return: A tuple of (status, amount_paid_kobo) or None on failure.
        """
        app_logger.info(f"Verifying Paystack transaction for ref: {reference}")
        response = await self._make_request("GET", f"/transaction/verify/{reference}")

        if response and response.get("status"):
            data = response.get("data", {})
            status = data.get("status")  # e.g., "success", "failed", "abandoned"
            amount_paid = data.get("amount")
            return status, amount_paid

        app_logger.warning(f"Failed to verify transaction {reference}.")
        return None


# A single, reusable instance of the service
paystack_service = PaystackService(secret_key=settings.PAYSTACK_SECRET_KEY)