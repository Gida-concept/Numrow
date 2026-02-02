from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import settings
from bot.router import main_router
from security.rate_limit import RateLimitMiddleware
from utils.logger import app_logger
from database.connection import get_db_session

# --- Bot and Dispatcher Initialization ---

# For FSM, we need to specify a storage. MemoryStorage is fine for simple cases.
# For production, you might want to use a persistent storage like RedisStorage.
storage = MemoryStorage()

# Create Bot and Dispatcher instances
bot = Bot(token=settings.BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=storage)

# --- Middleware Registration ---

# Register our custom rate-limiting middleware.
# This will apply to all incoming updates.
dp.update.middleware(RateLimitMiddleware(limit=3, period=1))
app_logger.info("Rate limiting middleware registered.")

# --- Router Inclusion ---

# Include the main router that contains all command and callback handlers.
dp.include_router(main_router)
app_logger.info("Main router included.")

# Pass the SQLAlchemy session factory to the dispatcher context
# so it can be used in handlers via dependency injection.
dp["session_factory"] = get_db_session