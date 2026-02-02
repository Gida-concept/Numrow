import asyncio
import re
from datetime import datetime, timezone

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from models.number import Number
from models.sms import Sms
from services.pva_service import pva_service
from database.redis import redis_client
from config.constants import REDIS_SMS_LAST_ID_PREFIX
from utils.logger import app_logger
import bot.messages as msg

# Polling interval in seconds.
POLLING_INTERVAL_SECONDS = 15


def _extract_code(text: str) -> str:
    """
    A simple helper to extract a verification code from SMS text.
    This looks for a sequence of 4-8 digits.
    """
    match = re.search(r'\b\d{4,8}\b', text)
    return match.group(0) if match else "N/A"


async def sms_polling_worker(bot: Bot, session_factory):
    """
    The main worker function that polls for SMS messages.
    """
    app_logger.info("SMS Polling Worker started.")
    while True:
        try:
            async with session_factory() as session:
                now_utc = datetime.now(timezone.utc)

                # 1. Find all active, non-expired numbers
                query = (
                    select(Number)
                    .options(selectinload(Number.user))  # Eagerly load the user to get their telegram_id
                    .where(Number.status == "active", Number.expires_at > now_utc)
                )
                result = await session.execute(query)
                active_numbers = result.scalars().all()

                if not active_numbers:
                    app_logger.debug("No active numbers to poll. Sleeping...")

                for number in active_numbers:
                    app_logger.debug(
                        f"Polling SMS for number {number.phone_number} (PVA ID: {number.pva_activation_id})")

                    # 2. Poll the PVA service
                    sms_data = await pva_service.get_sms(number.pva_activation_id)
                    if not sms_data or sms_data.get("status") != "OK":
                        if sms_data and sms_data.get("status") != "WAITING":
                            # Handle terminal statuses from PVA provider (e.g., CANCELED, BANNED)
                            app_logger.warning(
                                f"PVA status for {number.phone_number} is '{sms_data.get('status')}'. Deactivating.")
                            number.status = "expired"
                            await session.commit()
                        continue

                    # 3. Process new SMS
                    pva_sms_id = f"{number.pva_activation_id}_{sms_data.get('code')}"  # Create a unique ID for the SMS
                    sms_text = sms_data.get('code')  # PVA APIs often return the full text in the 'code' field

                    # Use Redis to check if we've already processed this exact SMS
                    redis_key = f"{REDIS_SMS_LAST_ID_PREFIX}:{number.id}"
                    last_seen_sms_id = await redis_client.get(redis_key)

                    if last_seen_sms_id != pva_sms_id:
                        app_logger.info(f"New SMS received for number {number.phone_number}!")

                        # 4. Save to DB and notify user
                        verification_code = _extract_code(sms_text)

                        new_sms = Sms(
                            number_id=number.id,
                            pva_sms_id=pva_sms_id,
                            full_text=sms_text,
                            verification_code=verification_code
                        )
                        session.add(new_sms)

                        # Send notification to user
                        await bot.send_message(
                            chat_id=number.user.telegram_id,
                            text=msg.new_sms_message(verification_code, sms_text)
                        )

                        await session.commit()
                        await redis_client.set(redis_key, pva_sms_id)  # Update the last seen SMS ID
                        app_logger.info(
                            f"SMS for number {number.id} processed and sent to user {number.user.telegram_id}")

                # Check for any numbers that expired based on our DB time
                expired_numbers_query = select(Number).where(Number.status == "active", Number.expires_at <= now_utc)
                expired_result = await session.execute(expired_numbers_query)
                for number in expired_result.scalars().all():
                    app_logger.info(f"Number {number.phone_number} expired based on internal timer. Deactivating.")
                    number.status = "expired"
                    # Optionally, notify the user their number has expired
                    # await bot.send_message(chat_id=number.user.telegram_id, text=msg.NUMBER_EXPIRED)

                await session.commit()

        except Exception as e:
            app_logger.critical(f"Critical error in SMS worker: {e}", exc_info=True)

        # Wait before the next polling cycle
        await asyncio.sleep(POLLING_INTERVAL_SECONDS)