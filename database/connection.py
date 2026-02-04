from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from typing import AsyncGenerator

from config.settings import settings

# Create an asynchronous engine to connect to the database.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

# Create a factory for asynchronous database sessions.
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injector that provides a database session.
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """
    Creates all database tables based on SQLAlchemy models.
    """
    # Import Base FIRST
    from models.base import Base
    
    # CRITICAL: Import ALL models to register them with the metadata
    from models.user import User
    from models.payment import Payment
    from models.number import Number
    from models.sms import Sms
    from models.rental import Rental
    
    async with engine.begin() as conn:
        # This will WIPE your database clean and recreate all tables with the new schema.
        await conn.run_sync(Base.metadata.drop_all) # <-- TEMPORARILY UNCOMMENTED
        await conn.run_sync(Base.metadata.create_all)
