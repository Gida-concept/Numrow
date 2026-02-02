import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the project root directory
# This helps in creating absolute paths, e.g., for a local SQLite DB or log files.
# It finds the directory where run.py is located.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    """
    Application settings are loaded from environment variables.
    Pydantic's BaseSettings makes this process declarative and type-safe.
    """
    # --- Core Bot Settings ---
    BOT_TOKEN: str = Field(..., description="Your Telegram Bot API token from @BotFather")

    # --- API Keys ---
    PAYSTACK_SECRET_KEY: str = Field(..., description="Your Paystack secret API key")
    PVA_API_KEY: str = Field(..., description="API key for the PVA service")

    # --- Database Configuration ---
    # Example for PostgreSQL: postgresql+asyncpg://user:password@host:port/dbname
    DATABASE_URL: str = Field(..., description="Asynchronous database connection string")

    # --- Redis Configuration ---
    REDIS_HOST: str = Field("127.0.0.1", description="Redis server host")
    REDIS_PORT: int = Field(6379, description="Redis server port")

    # --- Pricing Engine Rules (as per blueprint) ---
    PRICE_MARKUP_PERCENTAGE: int = Field(
        100,
        description="Internal markup percentage. 100 means 2x the original price."
    )
    FX_RATE_CAP: int = Field(
        1600,
        description="The maximum NGN to USD exchange rate to use. Acts as a safety cap."
    )

    # --- Logging Configuration ---
    LOG_LEVEL: str = Field("INFO", description="Logging level (e.g., DEBUG, INFO, WARNING, ERROR)")

    # Pydantic settings configuration
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, '.env'),  # Load from .env file in the project root
        env_file_encoding='utf-8',
        case_sensitive=False,  # Environment variables are case-insensitive
        extra='ignore'  # Ignore extra fields from .env
    )


# Create a single, importable instance of the settings
settings = Settings()