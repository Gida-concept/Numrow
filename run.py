import asyncio
import sys
from aiohttp import web
import json
import hmac
import hashlib

from aiogram.types import BotCommand

from config.settings import settings
from utils.logger import app_logger
from bot.main import bot, dp
from database.connection import init_db, async_session_factory
from workers.sms_worker import sms_polling_worker
from workers.rental_worker import rental_status_worker
from workers.payment_worker import process_webhook_event

async def paystack_webhook_handler(request: web.Request):
    try:
        body = await request.read()
        signature = request.headers.get('x-paystack-signature')
        calculated_signature = hmac.new(settings.PAYSTACK_SECRET_KEY.encode('utf-8'), body, hashlib.sha512).hexdigest()
        if signature != calculated_signature:
            app_logger.error("Invalid Paystack signature.")
            return web.Response(status=401)
        payload = json.loads(body)
        app_logger.critical(">>> PAYSTACK WEBHOOK RECEIVED <<<")
        async with async_session_factory() as session:
            success = await process_webhook_event(bot, session, payload)
        if success: return web.Response(status=200)
        else: return web.Response(status=400)
    except Exception as e:
        app_logger.error(f"Error processing Paystack webhook: {e}", exc_info=True)
        return web.Response(status=500)

async def set_bot_commands():
    commands = [BotCommand(command="start", description="Start/Restart the bot"), BotCommand(command="help", description="Get help")]
    await bot.set_my_commands(commands)
    app_logger.info("Bot commands set successfully.")

async def start_bot_polling():
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

async def main():
    app_logger.info("Application starting up...")
    try:
        await bot.get_me()
        await set_bot_commands()
        await init_db()
        app_logger.info("Bot, commands, and database initialized successfully.")
    except Exception as e:
        app_logger.critical(f"Initialization failed: {e}", exc_info=True)
        sys.exit(1)

    app = web.Application()
    app.router.add_post("/webhook/paystack", paystack_webhook_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8443)
    await site.start()
    app_logger.info("Webhook server started on port 8443.")

    sms_worker_task = asyncio.create_task(sms_polling_worker(bot, async_session_factory))
    rental_worker_task = asyncio.create_task(rental_status_worker(bot, async_session_factory))

    try:
        app_logger.info("Starting bot polling...")
        await start_bot_polling()
    finally:
        app_logger.warning("Shutdown sequence initiated...")
        sms_worker_task.cancel()
        rental_worker_task.cancel()
        try:
            await asyncio.gather(sms_worker_task, rental_worker_task, return_exceptions=True)
        except asyncio.CancelledError:
            app_logger.info("Background workers cancelled successfully.")
        await runner.cleanup()
        await bot.session.close()
        app_logger.info("Shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        app_logger.warning("Application was stopped manually.")
