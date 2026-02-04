import asyncio
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from models.number import Number
from utils.logger import app_logger
from services.pva_service import pva_service
from workers.pricing_worker import get_final_price
from bot.keyboards import rental_renewal_keyboard

RENEWAL_WARNING_DAYS = 3
POLLING_INTERVAL_SECONDS = 3600 # Check once per hour

async def rental_status_worker(bot: Bot, session_factory):
    app_logger.info("Rental Status Worker started.")
    while True:
        try:
            async with session_factory() as session:
                now_utc = datetime.now(timezone.utc)
                warning_date = now_utc + timedelta(days=RENEWAL_WARNING_DAYS)
                
                # --- 1. Find numbers that are about to expire to send a warning ---
                expiring_query = (
                    select(Number)
                    .options(selectinload(Number.user))
                    .where(
                        Number.is_rent == True,
                        Number.status == "active",
                        Number.expires_at <= warning_date,
                        Number.renewal_notice_sent == False # Only send once
                    )
                )
                expiring_numbers = (await session.execute(expiring_query)).scalars().all()

                for number in expiring_numbers:
                    app_logger.info(f"Rental number {number.phone_number} is expiring soon. Sending warning.")
                    
                    # Get the renewal price
                    price_ngn, _, __ = await get_final_price(
                        country_id=number.country_code,
                        service_id=number.service_code,
                        is_rent=True
                    )

                    if price_ngn:
                        try:
                            # Send renewal warning message with the price
                            await bot.send_message(
                                chat_id=number.user.telegram_id,
                                text=f"⚠️ Your rental for {number.phone_number} will expire in less than {RENEWAL_WARNING_DAYS} days. Renew now to keep your number.",
                                reply_markup=rental_renewal_keyboard(number.id, price_ngn)
                            )
                            number.renewal_notice_sent = True
                            app_logger.info(f"Sent renewal notice for number {number.phone_number} to user {number.user.telegram_id}")
                        except Exception as e:
                            app_logger.error(f"Failed to send renewal notice to user {number.user.telegram_id}: {e}")
                    else:
                        app_logger.warning(f"Could not get renewal price for number {number.phone_number}. Skipping notice.")

                # --- 2. Find numbers that have already expired ---
                expired_query = (
                    select(Number)
                    .options(selectinload(Number.user))
                    .where(
                        Number.is_rent == True,
                        Number.status == "active",
                        Number.expires_at <= now_utc
                    )
                )
                expired_numbers = (await session.execute(expired_query)).scalars().all()
                for number in expired_numbers:
                    app_logger.info(f"Rental number {number.phone_number} has expired.")
                    number.status = "expired"
                    try:
                        await bot.send_message(chat_id=number.user.telegram_id, text=f"Your rental for {number.phone_number} has expired.")
                    except Exception as e:
                        app_logger.error(f"Failed to send rental expiration notice to user {number.user.telegram_id}: {e}")
                
                await session.commit()

        except Exception as e:
            app_logger.critical(f"Critical error in Rental Status Worker: {e}", exc_info=True)

        await asyncio.sleep(POLLING_INTERVAL_SECONDS)
