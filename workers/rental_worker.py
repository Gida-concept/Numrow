import asyncio
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from models.number import Number
from utils.logger import app_logger
import bot.messages as msg

# How many days before expiry to send a warning
RENEWAL_WARNING_DAYS = 3
POLLING_INTERVAL_SECONDS = 3600 # Check once per hour

async def rental_status_worker(bot: Bot, session_factory):
    """
    A dedicated worker to check the status of rented numbers and send expiry warnings.
    """
    app_logger.info("Rental Status Worker started.")
    while True:
        try:
            async with session_factory() as session:
                now_utc = datetime.now(timezone.utc)
                warning_date = now_utc + timedelta(days=RENEWAL_WARNING_DAYS)

                # --- 1. Find numbers that are about to expire ---
                # We need to join with the Rental model to check the 'is_rent' flag
                # For now, we'll assume a way to identify rentals. Let's add a flag to the Number model.
                
                # This requires a schema change. We'll handle this in the next step.
                # Placeholder logic:
                expiring_query = (
                    select(Number)
                    .options(selectinload(Number.user))
                    .where(
                        Number.is_rent == True,
                        Number.status == "active",
                        Number.expires_at <= warning_date,
                        Number.renewal_notice_sent == False # Add this new field
                    )
                )
                # result = await session.execute(expiring_query)
                # for number in result.scalars().all():
                #     # Send renewal warning
                #     # Update number.renewal_notice_sent = True

                # --- 2. Find numbers that have expired ---
                expired_query = (
                    select(Number)
                    .options(selectinload(Number.user))
                    .where(
                        Number.is_rent == True,
                        Number.status == "active",
                        Number.expires_at <= now_utc
                    )
                )
                result = await session.execute(expired_query)
                for number in result.scalars().all():
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
