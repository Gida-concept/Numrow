import asyncio
import sys
from aiohttp import web

from aiogram.types import BotCommand

from utils.logger import app_logger
from bot.main import bot, dp
from database.connection import init_db, async_session_factory
from workers.sms_worker import sms_polling_worker
from workers.payment_worker import process_webhook_event

# --- Webhook Handler ---
async def paystack_webhook_handler(request: web.Request):
    """
    Handles incoming webhooks from Paystack.
    """
    try:
        payload = await request.json()
        app_logger.info(f"Received Paystack webhook: {payload.get('event')}")

        # You should add signature verification here for production security
        # For now, we process it directly.
        
        async with async_session_factory() as session:
            success = await process_webhook_event(session, payload)
        
        if success:
            return web.Response(status=200) # Tell Paystack we received it
        else:
            # If processing fails, tell Paystack something is wrong
            return web.Response(status=400)

    except Exception as e:
        app_logger.error(f"Error processing Paystack webhook: {e}", exc_info=True)
        return web.Response(status=500)


async def set_bot_commands():
    """Sets the bot's command menu."""
    commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="help", description="Get help"),
    ]
    await bot.set_my_commands(commands)
    app_logger.info("Bot commands set successfully.")


async def start_bot_polling():
    """Starts the bot's polling loop."""
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

async def main():
    """Configures and runs all application components."""
    app_logger.info("Application starting up...")

    # Initialize bot and database
    try:
        await bot.get_me()
        await set_bot_commands()
        await init_db()
        app_logger.info("Bot, commands, and database initialized successfully.")
    except Exception as e:
        app_logger.critical(f"Initialization failed: {e}", exc_info=True)
        sys.exit(1)

    # --- Start Web Server for Webhooks ---
    app = web.Application()
    app.router.add_post("/webhook/paystack", paystack_webhook_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    # Run on localhost and port 8443
    site = web.TCPSite(runner, '0.0.0.0', 8443) # <-- PORT CHANGED HERE
    await site.start()
    app_logger.info("Webhook server started on port 8443.") # <-- LOG MESSAGE UPDATED

    # --- Start Background Workers ---
    sms_worker_task = asyncio.create_task(sms_polling_worker(bot, async_session_factory))
    
    # --- Start Bot Polling ---
    try:
        app_logger.info("Starting bot polling...")
        await start_bot_polling()
    finally:
        app_logger.warning("Shutdown sequence initiated...")
        sms_worker_task.cancel()
        await runner.cleanup()
        await bot.session.close()
        app_logger.info("Shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        app_logger.warning("Application stopped manually.")
