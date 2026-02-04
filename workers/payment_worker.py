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
from bot.keyboards import refresh_sms_keyboard

async def create_payment_link(session: AsyncSession, user_id: int, final_ngn_price: int, price_ref: str) -> Optional[str]:
    try:
        user = await session.get(User, user_id)
        if not user:
            app_logger.error(f"Cannot create payment for non-existent user ID {user_id}")
            return None
        
        user_email = f"user_{user.telegram_id}@numrow.com"
        amount_kobo = final_ngn_price * 100
        transaction_ref = f"pva-{user.id}-{uuid.uuid4().hex[:8]}"
        new_payment = Payment(user_id=user.id, amount_ngn=amount_kobo, status="pending", paystack_ref=transaction_ref, locked_price_ref=price_ref)
        session.add(new_payment)
        await session.commit()
        await session.refresh(new_payment)
        app_logger.info(f"Created pending payment record ID {new_payment.id} with ref {transaction_ref}")
        lock_key = f"{REDIS_PRICING_LOCK_PREFIX}:{new_payment.id}"
        await redis_client.set(lock_key, price_ref, ex=PRICE_LOCK_DURATION)
        payment_url = await paystack_service.initialize_transaction(email=user_email, amount_kobo=amount_kobo, reference=transaction_ref)
        return payment_url
    except Exception as e:
        app_logger.error(f"Failed to create payment link: {e}", exc_info=True)
        await session.rollback()
        return None

async def process_webhook_event(bot, session: AsyncSession, payload: dict) -> bool:
    event, data = payload.get("event"), payload.get("data")
    if event != "charge.success": return False
    reference = data.get("reference")
    if not reference: return False

    query = select(Payment).where(Payment.paystack_ref == reference).options(selectinload(Payment.user))
    payment = (await session.execute(query)).scalar_one_or_none()
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
        # Check if this is a renewal payment
        if payment.locked_price_ref.startswith("renewal:"):
            number_to_renew_id = int(payment.locked_price_ref.split(':')[1])
            number_to_renew = await session.get(Number, number_to_renew_id)
            
            if not number_to_renew:
                app_logger.error(f"Cannot renew non-existent number ID {number_to_renew_id}")
                return False

            countries = await pva_service.get_countries(is_rent=True)
            country_name = next((c['name'] for c in countries if c['id'] == number_to_renew.country_code), None)
            
            success = await pva_service.renew_rental_number(
                service_id=number_to_renew.service_code, country_id=number_to_renew.country_code,
                country_name=country_name, phone_number=number_to_renew.phone_number
            )

            if success:
                # Update the expiry date in our database (assuming 3-day renewal)
                new_expiry = number_to_renew.expires_at + timedelta(days=3)
                number_to_renew.expires_at = new_expiry
                number_to_renew.renewal_notice_sent = False # Reset the notice flag
                await session.commit()
                app_logger.info(f"Successfully updated expiry for number {number_to_renew.phone_number} to {new_expiry}")
                await bot.send_message(chat_id=payment.user.telegram_id, text=f"✅ Your rental for {number_to_renew.phone_number} has been successfully renewed!")
            else:
                app_logger.error(f"Failed to renew number {number_to_renew.phone_number} via API.")
                await bot.send_message(chat_id=payment.user.telegram_id, text=f"⚠️ We received your payment, but there was an error renewing your number. Please contact support.")
        
        # Original logic for a NEW number purchase
        else:
            parts = payment.locked_price_ref.split(":")
            country_id, service_id, number_type = parts[1], parts[2], parts[3]
            is_rent = (number_type == 'rent')

            countries = await pva_service.get_countries(is_rent=is_rent)
            country_name = next((c['name'] for c in countries if c['id'] == country_id), None)
            if not country_name: return False

            app_logger.info(f"Triggering number purchase for service ID '{service_id}' in country '{country_name}'.")
            
            purchased_number_info = await pva_service.buy_number(service_id=service_id, country_id=country_id, country_name=country_name, is_rent=is_rent)

            if purchased_number_info:
                app_logger.info(f"Successfully purchased number for payment {payment.id}: {purchased_number_info}")
                
                if is_rent: expiry_delta = timedelta(days=3)
                else: expiry_delta = timedelta(minutes=DEFAULT_TEMP_DURATION_MINUTES)
                
                new_number = Number(
                    phone_number=purchased_number_info['phone_number'],
                    pva_activation_id=purchased_number_info['activation_id'],
                    service_code=service_id, country_code=country_id, status="active",
                    is_rent=is_rent,
                    expires_at=datetime.now(timezone.utc) + expiry_delta,
                    user_id=payment.user_id, payment_id=payment.id
                )
                session.add(new_number)
                await session.commit()
                await session.refresh(new_number)
                
                expiry_string = f"in {expiry_delta.days} days" if is_rent else f"in {expiry_delta.seconds // 60} minutes"
                await bot.send_message(
                    chat_id=payment.user.telegram_id, 
                    text=msg.number_issued_message(new_number.phone_number, expiry_string),
                    reply_markup=refresh_sms_keyboard(new_number.id)
                )
            else:
                app_logger.error(f"Failed to purchase number for successful payment {payment.id}.")
                await bot.send_message(chat_id=payment.user.telegram_id, text="We received your payment, but there was an error ordering your number. Please contact support.")
    
    except Exception as e:
        app_logger.critical(f"Error triggering action for payment {payment.id}: {e}", exc_info=True)
        return False
    return True
