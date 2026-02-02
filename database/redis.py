import redis.asyncio as redis
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from config.settings import settings

# Create an asynchronous Redis connection pool.
# A connection pool is more efficient than creating a new connection for every request.
# decode_responses=True ensures that values retrieved from Redis are automatically
# decoded from bytes to UTF-8 strings, which is usually what we want.
redis_pool = redis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,  # Default Redis database
    decode_responses=True
)


async def get_redis_client() -> redis.Redis:
    """
    Returns a Redis client from the connection pool.
    This provides a direct, low-level client for commands.
    """
    return redis.Redis(connection_pool=redis_pool)


@asynccontextmanager
async def redis_context() -> AsyncGenerator[redis.Redis, None]:
    """
    An async context manager for acquiring a Redis client.
    Ensures that the connection is properly managed.

    Usage:
    async with redis_context() as redis_client:
        await redis_client.set("key", "value")
    """
    client = await get_redis_client()
    try:
        yield client
    finally:
        # With a connection pool, 'close' returns the connection to the pool.
        # It doesn't actually close the underlying TCP connection.
        await client.close()


# A global client instance can also be useful for simple, one-off commands,
# though using the context manager or dependency injection is often cleaner.
# This client will be used by workers or other parts of the app.
redis_client = redis.Redis(connection_pool=redis_pool)