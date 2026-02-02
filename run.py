import asyncio
import sys

from utils.logger import app_logger
from bot.main import bot, dp
from database.connection import init_db, async_session_factory
from workers.sms_worker import sms_polling_worker


async def main():
    """The main function that configures and starts the application."""

    app_logger.info("Application starting up...")

    # Log bot information for verification
    try:
        bot_info = await bot.get_me()
        app_logger.info(f"Bot successfully initialized: {bot_info.full_name} [@{bot_info.username}]")
    except Exception as e:
        app_logger.critical(f"Failed to initialize bot: {e}. Check BOT_TOKEN.", exc_info=True)
        sys.exit(1)

    # Initialize the database.
    # NOTE: For production, it's highly recommended to use Alembic for migrations
    # instead of running create_all() on every start.
    try:
        app_logger.info("Initializing database...")
        await init_db()
        app_logger.info("Database initialized successfully.")
    except Exception as e:
        app_logger.critical(f"Failed to initialize database: {e}", exc_info=True)
        sys.exit(1)

    # Start the background SMS polling worker.
    app_logger.info("Starting background SMS worker...")
    sms_worker_task = asyncio.create_task(
        sms_polling_worker(bot, async_session_factory)
    )

    # Start polling for Telegram updates.
    # This will run until the process is stopped.
    try:
        app_logger.info("Starting bot polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        app_logger.warning("Bot polling stopped. Shutting down...")
        # Gracefully stop the background worker
        sms_worker_task.cancel()
        try:
            await sms_worker_task
        except asyncio.CancelledError:
            app_logger.info("SMS worker task cancelled successfully.")

        # Close the bot's session
        await bot.session.close()
        app_logger.info("Bot session closed. Shutdown complete.")


if __name__ == "__main__":
    # This block runs when the script is executed directly.
    # It handles the main async loop and graceful shutdown on CTRL+C.
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        app_logger.warning("Application was stopped manually.")
    except Exception as e:
        app_logger.critical(f"A critical error caused the application to stop: {e}", exc_info=True)
        sys.exit(1)