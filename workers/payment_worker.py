import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.user import User
from models.payment import Payment
from services.paystack_service import paystack_service
from services.pva_service import pva_service  # To trigger number purchase
from utils.logger import app_logger
from config.constants import REDIS_PRICING_LOCK_PREFIX, PRICE_LOCK_DURATION
from database.redis import redis_client


async def create_payment_link(
        session: AsyncSession,
        user_id: int,  # This is our DB user.id, not telegram_id
        final_ngn_price: int,
        price_ref: str
) -> Optional[str]:
    """
    Creates a payment record in the DB and gets a Paystack payment link.
    """
    try:
        # 1. Get user email (using a placeholder for now)
        user = await session.get(User, user_id)
        if not user:
            app_logger.error(f"Cannot create payment. User with DB ID {user_id} not found.")
            return None

        # Paystack requires an email. We'll generate a placeholder.
        user_email = f"user_{user.telegram_id}@example.com"

        # 2. Convert NGN to Kobo for Paystack
        amount_kobo = final_ngn_price * 100

        # 3. Generate a unique reference for this transaction
        transaction_ref = f"pva-{user.id}-{uuid.uuid4().hex[:8]}"

        # 4. Create and store the payment record
        new_payment = Payment(
            user_id=user.id,
            amount_ngn=amount_kobo,
            status="pending",
            paystack_ref=transaction_ref,
            locked_price_ref=price_ref
        )
        session.add(new_payment)
        await session.commit()
        await session.refresh(new_payment)
        app_logger.info(f"Created pending payment record ID {new_payment.id} with ref {transaction_ref}")

        # 5. Lock the price in Redis
        lock_key = f"{REDIS_PRICING_LOCK_PREFIX}:{new_payment.id}"
        await redis_client.set(lock_key, price_ref, ex=PRICE_LOCK_DURATION)
        app_logger.info(f"Price ref '{price_ref}' locked for payment {new_payment.id}")

        # 6. Initialize Paystack transaction
        payment_url = await paystack_service.initialize_transaction(
            email=user_email,
            amount_kobo=amount_kobo,
            reference=transaction_ref
        )

        return payment_url

    except Exception as e:
        app_logger.error(f"Failed to create payment link: {e}", exc_info=True)
        await session.rollback()
        return None


async def process_webhook_event(session: AsyncSession, payload: dict) -> bool:
    """
    Processes a 'charge.success' event from a Paystack webhook.
    Returns True if the event was processed successfully, False otherwise.
    """
    event = payload.get("event")
    data = payload.get("data")

    if event != "charge.success":
        app_logger.debug(f"Ignoring non-success webhook event: {event}")
        return False

    reference = data.get("reference")
    if not reference:
        app_logger.warning("Webhook received without a reference.")
        return False

    # 1. Find the payment in our database
    query = select(Payment).where(Payment.paystack_ref == reference)
    result = await session.execute(query)
    payment = result.scalar_one_or_none()

    if not payment:
        app_logger.error(f"Webhook for unknown reference '{reference}' received.")
        return False

    if payment.status == "successful":
        app_logger.info(f"Webhook for already successful payment '{reference}' received. Ignoring.")
        return True  # Acknowledge but do nothing

    # 2. Double-check with Paystack API as a security measure
    verified_status, verified_amount_kobo = await paystack_service.verify_transaction(reference)

    if verified_status != "success":
        app_logger.warning(f"Webhook-triggered verification for '{reference}' failed. Status: {verified_status}")
        payment.status = "failed"
        await session.commit()
        return False

    if verified_amount_kobo != payment.amount_ngn:
        app_logger.error(
            f"CRITICAL: Amount mismatch for '{reference}'. "
            f"DB: {payment.amount_ngn}, Paystack: {verified_amount_kobo}. MANUAL REVIEW REQUIRED."
        )
        payment.status = "disputed"  # Use a special status for manual checks
        await session.commit()
        return False

    # 3. Update payment status
    payment.status = "successful"
    await session.commit()
    app_logger.info(f"Payment {payment.id} (ref: {reference}) successfully updated to 'successful'.")

    # 4. Trigger the number purchase (as per blueprint)
    try:
        # Parse country/service from the locked price reference
        # e.g., "pricing:0:wa:temporary" -> country=0, service=wa
        _, country_id, service_id, _ = payment.locked_price_ref.split(":")

        app_logger.info(f"Triggering number purchase for service '{service_id}', country '{country_id}'.")
        purchased_number_info = await pva_service.buy_number(service=service_id, country=country_id)

        if purchased_number_info:
            app_logger.info(f"Successfully purchased number for payment {payment.id}: {purchased_number_info}")
            # Here we would create a `Number` record in the DB and link it to the payment.
            # We'll build that model and logic next.
        else:
            app_logger.error(
                f"Failed to purchase number for successful payment {payment.id}. MANUAL INTERVENTION NEEDED.")
            # TODO: Implement a retry or refund mechanism.

    except Exception as e:
        app_logger.critical(f"Error triggering number purchase for payment {payment.id}: {e}", exc_info=True)
        return False

    return True