import asyncio
import sys

from aiogram.types import BotCommand

from utils.logger import app_logger
from bot.main import bot, dp
from database.connection import init_db, async_session_factory
from workers.sms_worker import sms_polling_worker


async def set_bot_commands():
    """
    Sets the bot's command menu that users see when they type '/'
    """
    commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="help", description="Get help"),
    ]
    await bot.set_my_commands(commands)
    app_logger.info("Bot commands set successfully.")


async def main():
    """The main function that configures and starts the application."""
    
    app_logger.info("Application starting up...")

    try:
        bot_info = await bot.get_me()
        app_logger.info(f"Bot successfully initialized: {bot_info.full_name} [@{bot_info.username}]")
    except Exception as e:
        app_logger.critical(f"Failed to initialize bot: {e}. Check BOT_TOKEN.", exc_info=True)
        sys.exit(1)

    # Set bot commands
    try:
        await set_bot_commands()
    except Exception as e:
        app_logger.warning(f"Failed to set bot commands: {e}")

    # Initialize the database
    try:
        app_logger.info("Initializing database...")
        await init_db()
        app_logger.info("Database initialized successfully.")
    except Exception as e:
        app_logger.critical(f"Failed to initialize database: {e}", exc_info=True)
        sys.exit(1)
    
    # Start the background SMS polling worker
    app_logger.info("Starting background SMS worker...")
    sms_worker_task = asyncio.create_task(
        sms_polling_worker(bot, async_session_factory)
    )

    # Start polling for Telegram updates
    try:
        app_logger.info("Starting bot polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        app_logger.warning("Bot polling stopped. Shutting down...")
        sms_worker_task.cancel()
        try:
            await sms_worker_task
        except asyncio.CancelledError:
            app_logger.info("SMS worker task cancelled successfully.")
        
        await bot.session.close()
        app_logger.info("Bot session closed. Shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        app_logger.warning("Application was stopped manually.")
    except Exception as e:
        app_logger.critical(f"A critical error caused the application to stop: {e}", exc_info=True)
        sys.exit(1)
