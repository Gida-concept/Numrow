from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from config.settings import settings
from bot.router import main_router
from bot.middlewares import DbSessionMiddleware
from security.rate_limit import RateLimitMiddleware
from utils.logger import app_logger
from database.connection import async_session_factory

# --- Bot and Dispatcher Initialization ---

storage = MemoryStorage()

bot = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=storage)

# --- Middleware Registration ---
# Register middlewares on the ROUTER, not the dispatcher

main_router.message.middleware(DbSessionMiddleware(session_pool=async_session_factory))
main_router.callback_query.middleware(DbSessionMiddleware(session_pool=async_session_factory))
app_logger.info("Database session middleware registered on router.")

main_router.message.middleware(RateLimitMiddleware(limit=3, period=1))
main_router.callback_query.middleware(RateLimitMiddleware(limit=3, period=1))
app_logger.info("Rate limiting middleware registered on router.")

# --- Router Inclusion ---

dp.include_router(main_router)
app_logger.info("Main router included.")
