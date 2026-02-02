from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

# 'CancelHandler' is removed. We don't need a special import to stop processing.

from database.redis import redis_client
from config.constants import REDIS_RATE_LIMIT_PREFIX
from utils.logger import app_logger

class RateLimitMiddleware(BaseMiddleware):
    """
    A middleware to prevent spam by rate-limiting users.
    """
    def __init__(self, limit: int = 3, period: int = 1):
        """
        :param limit: The maximum number of requests allowed.
        :param period: The time period in seconds.
        """
        self.limit = limit
        self.period = period
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        The main middleware logic. This is executed for every incoming update.
        """
        user: User | None = data.get("event_from_user")

        if not user:
            return await handler(event, data)

        key = f"{REDIS_RATE_LIMIT_PREFIX}:{user.id}"

        async with redis_client.pipeline() as pipe:
            pipe.incr(key)
            pipe.expire(key, self.period)
            requests_count, _ = await pipe.execute()

        if int(requests_count) > self.limit:
            app_logger.warning(
                f"Rate limit exceeded for user {user.id} (@{user.username}). "
                f"Count: {requests_count} in {self.period}s."
            )
            # To cancel the handler in aiogram 3.x, we simply 'return'
            # without calling the next handler. No exception is needed.
            return
        
        app_logger.debug(f"User {user.id} request count: {requests_count}")

        return await handler(event, data)
