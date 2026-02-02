from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from typing import AsyncGenerator

from config.settings import settings

# Create an asynchronous engine to connect to the database.
# The 'echo=False' parameter prevents SQLAlchemy from logging every SQL query.
# Set to 'True' for debugging database interactions.
# 'pool_pre_ping=True' checks the health of connections before using them.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Set to True to see generated SQL statements
    pool_pre_ping=True,
)

# Create a factory for asynchronous database sessions.
# 'autoflush=False' prevents automatic flushing, giving us more control.
# 'expire_on_commit=False' is important for async code, as objects accessed
# after a commit might otherwise be expired and need re-fetching.
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injector that provides a database session.

    This is a generator that yields a single session and ensures it's
    closed correctly after the operation is complete.
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            # The 'async with' block automatically handles commit, rollback, and closing.
            # However, you might want to add explicit commit/rollback logic in your
            # business logic layer depending on the use case.
            await session.close()


async def init_db():
    """
    A utility function to create all database tables based on SQLAlchemy models.
    This would typically be run once when the application starts up or
    managed via a migration tool like Alembic in production.
    """
    # This import is done here to avoid circular dependency issues
    # as models will import a Base from this module (or a shared one).
    from models.base import Base

    async with engine.begin() as conn:
        # In a real app, you would use Alembic migrations instead of this.
        # await conn.run_sync(Base.metadata.drop_all) # Uncomment to reset DB
        await conn.run_sync(Base.metadata.create_all)