import asyncio
import re
from datetime import datetime, timezone

from aiogram import Bot
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from models.number import Number
from models.sms import Sms
from services.pva_service import pva_service
from database.redis import redis_client
from config.constants import REDIS_SMS_LAST_ID_PREFIX
from utils.logger import app_logger
import bot.messages as msg

POLLING_INTERVAL_SECONDS = 15

def _extract_code(text: str) -> str:
    """A simple helper to extract a verification code from SMS text."""
    match = re.search(r'\b\d{4,8}\b', text)
    return match.group(0) if match else "N/A"

async def sms_polling_worker(bot: Bot, session_factory):
    """The main worker function that polls for SMS messages."""
    app_logger.info("SMS Polling Worker started.")
    while True:
        try:
            async with session_factory() as session:
                now_utc = datetime.now(timezone.utc)
                
                query = (
                    select(Number)
                    .options(selectinload(Number.user))
                    .where(Number.status == "active", Number.expires_at > now_utc)
                )
                active_numbers = (await session.execute(query)).scalars().all()

                if not active_numbers:
                    app_logger.debug("No active numbers to poll. Sleeping...")
                
                for number in active_numbers:
                    app_logger.debug(f"Polling SMS for number {number.phone_number}")

                    # Use the is_rent flag to determine the API call type
                    is_rent = number.is_rent
                    countries = await pva_service.get_countries(is_rent=is_rent)
                    country_name = next((c['name'] for c in countries if c['id'] == number.country_code), None)

                    if not country_name:
                        app_logger.warning(f"Could not find country name for code {number.country_code}. Skipping.")
                        continue

                    sms_data = await pva_service.get_sms(
                        phone_number=number.phone_number,
                        service_id=number.service_code,
                        country_id=number.country_code,
                        country_name=country_name,
                        is_rent=is_rent
                    )
                    
                    if not sms_data or sms_data.get("status") != "OK":
                        if sms_data and sms_data.get("status") != "WAITING":
                            app_logger.warning(f"PVA status for {number.phone_number} is '{sms_data.get('status')}'. Deactivating.")
                            number.status = "expired"
                            await session.commit()
                        continue

                    sms_text = sms_data.get('code', '')
                    pva_sms_id = f"{number.pva_activation_id}_{hash(sms_text)}"
                    redis_key = f"{REDIS_SMS_LAST_ID_PREFIX}:{number.id}"
                    last_seen_sms_id = await redis_client.get(redis_key)

                    if last_seen_sms_id != pva_sms_id:
                        app_logger.info(f"New SMS received for number {number.phone_number}!")
                        verification_code = _extract_code(sms_text)
                        new_sms = Sms(number_id=number.id, pva_sms_id=pva_sms_id, full_text=sms_text, verification_code=verification_code)
                        session.add(new_sms)
                        await bot.send_message(chat_id=number.user.telegram_id, text=msg.new_sms_message(verification_code, sms_text))
                        await session.commit()
                        await redis_client.set(redis_key, pva_sms_id)
                        app_logger.info(f"SMS for number {number.id} processed and sent to user {number.user.telegram_id}")

                # This expiration logic now works for both temp and rent numbers
                expired_numbers_query = (
                    select(Number).options(selectinload(Number.user))
                    .where(Number.status == "active", Number.expires_at <= now_utc)
                )
                for number in (await session.execute(expired_numbers_query)).scalars().all():
                    app_logger.info(f"Number {number.phone_number} expired. Deactivating.")
                    number.status = "expired"
                    try:
                        expiry_msg = f"Your rental for {number.phone_number} has expired." if number.is_rent else msg.NUMBER_EXPIRED
                        await bot.send_message(chat_id=number.user.telegram_id, text=expiry_msg)
                        app_logger.info(f"Sent expiration notice for {number.phone_number} to user {number.user.telegram_id}")
                    except Exception as e:
                        app_logger.error(f"Failed to send expiration notice: {e}")
                
                await session.commit()

        except Exception as e:
            app_logger.critical(f"Critical error in SMS worker: {e}", exc_info=True)
        await asyncio.sleep(POLLING_INTERVAL_SECONDS)
