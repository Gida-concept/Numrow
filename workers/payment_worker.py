import time
import uuid
from typing import Optional
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from models.user import User
from models.payment import Payment
from models.number import Number
from services.paystack_service import paystack_service
from services.pva_service import pva_service
from utils.logger import app_logger
from config.constants import REDIS_PRICING_LOCK_PREFIX, PRICE_LOCK_DURATION, DEFAULT_TEMP_DURATION_MINUTES
from database.redis import redis_client
import bot.messages as msg
from bot.keyboards import refresh_sms_keyboard # <-- Import the new keyboard

async def create_payment_link(
    session: AsyncSession,
    user_id: int,
    final_ngn_price: int,
    price_ref: str
) -> Optional[str]:
    # ... (this function is correct and unchanged) ...
    try:
        user = await session.get(User, user_id)
        if not user:
            app_logger.error(f"Cannot create payment. User with DB ID {user_id} not found.")
            return None
        
        user_email = f"user_{user.telegram_id}@numrow.com"
        amount_kobo = final_ngn_price * 100
        transaction_ref = f"pva-{user.id}-{uuid.uuid4().hex[:8]}"

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

        lock_key = f"{REDIS_PRICING_LOCK_PREFIX}:{new_payment.id}"
        await redis_client.set(lock_key, price_ref, ex=PRICE_LOCK_DURATION)
        app_logger.info(f"Price ref '{price_ref}' locked for payment {new_payment.id}")

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

async def process_webhook_event(bot, session: AsyncSession, payload: dict) -> bool:
    """
    Processes a 'charge.success' event from a Paystack webhook.
    """
    # ... (the first part of this function is correct and unchanged) ...
    event = payload.get("event")
    data = payload.get("data")
    if event != "charge.success": return False
    reference = data.get("reference")
    if not reference: return False

    query = select(Payment).where(Payment.paystack_ref == reference).options(selectinload(Payment.user))
    result = await session.execute(query)
    payment = result.scalar_one_or_none()
    if not payment: return False
    if payment.status == "successful": return True

    verified_status, verified_amount_kobo = await paystack_service.verify_transaction(reference)
    if verified_status != "success":
        payment.status = "failed"
        await session.commit()
        return False
    if verified_amount_kobo != payment.amount_ngn:
        payment.status = "disputed"
        await session.commit()
        return False

    payment.status = "successful"
    await session.commit()
    app_logger.info(f"Payment {payment.id} (ref: {reference}) successfully updated.")

    try:
        parts = payment.locked_price_ref.split(":")
        country_id, service_id, number_type = parts[1], parts[2], parts[3]
        is_rent = (number_type == 'rent')

        countries = await pva_service.get_countries(is_rent=is_rent)
        country_name = next((c['name'] for c in countries if c['id'] == country_id), None)
        if not country_name: return False

        app_logger.info(f"Triggering number purchase for service ID '{service_id}' in country '{country_name}'.")
        
        purchased_number_info = await pva_service.buy_number(
            service_id=service_id, country_id=country_id,
            country_name=country_name, is_rent=is_rent
        )

        if purchased_number_info:
            app_logger.info(f"Successfully purchased number for payment {payment.id}: {purchased_number_info}")
            
            expiry_delta = timedelta(minutes=DEFAULT_TEMP_DURATION_MINUTES)
            new_number = Number(
                phone_number=purchased_number_info['phone_number'],
                pva_activation_id=purchased_number_info['activation_id'],
                service_code=service_id,
                country_code=country_id,
                status="active",
                expires_at=datetime.now(timezone.utc) + expiry_delta,
                user_id=payment.user_id,
                payment_id=payment.id
            )
            session.add(new_number)
            await session.commit()
            await session.refresh(new_number) # Get the new_number.id
            
            # Use the new keyboard when sending the number to the user
            expiry_string = f"in {expiry_delta.seconds // 60} minutes"
            await bot.send_message(
                chat_id=payment.user.telegram_id, 
                text=msg.number_issued_message(new_number.phone_number, expiry_string),
                reply_markup=refresh_sms_keyboard(new_number.id) # <-- USING THE NEW KEYBOARD
            )

        else:
            app_logger.error(f"Failed to purchase number for successful payment {payment.id}.")
            await bot.send_message(
                chat_id=payment.user.telegram_id,
                text="We received your payment, but there was an error ordering your number. Please contact support."
            )
    
    except Exception as e:
        app_logger.critical(f"Error triggering number purchase for payment {payment.id}: {e}", exc_info=True)
        return False

    return True
