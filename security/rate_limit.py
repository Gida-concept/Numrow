from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from aiogram.dispatcher.event.handler import CancelHandler

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

        # If the update is not from a user, we don't need to rate-limit it.
        if not user:
            return await handler(event, data)

        # 1. Construct the Redis key for this user.
        key = f"{REDIS_RATE_LIMIT_PREFIX}:{user.id}"

        # 2. Use a Redis pipeline for atomic operations.
        # This ensures that INCR and EXPIRE happen as a single transaction.
        async with redis_client.pipeline() as pipe:
            pipe.incr(key)
            pipe.expire(key, self.period)
            requests_count, _ = await pipe.execute()

        # 3. Check if the user has exceeded the limit.
        if int(requests_count) > self.limit:
            app_logger.warning(
                f"Rate limit exceeded for user {user.id} (@{user.username}). "
                f"Count: {requests_count} in {self.period}s."
            )
            # Cancel the processing of the current update.
            # The user's request will be ignored.
            raise CancelHandler()

        app_logger.debug(f"User {user.id} request count: {requests_count}")

        # 4. If the limit is not exceeded, proceed to the next handler.
        return await handler(event, data)