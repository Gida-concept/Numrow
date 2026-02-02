import sys
from loguru import logger

from config.settings import settings


def setup_logger():
    """
    Configures the Loguru logger for the application.

    This function removes any default handlers and adds a new one with
    a specific format and colorization. The log level is determined by the
    'LOG_LEVEL' setting in the application's configuration.
    """
    # Remove the default logger to ensure our configuration is the only one.
    logger.remove()

    # Add a new sink (output) to the logger.
    # sys.stderr is the standard error stream, a common place for logs.
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL.upper(),  # Set log level from config
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        colorize=True,  # Make logs colorful for better readability in terminals
        backtrace=True,  # Show full stack trace on exceptions
        diagnose=True,  # Add exception variable values for easier debugging
    )

    # You could also add a file sink here for production logging:
    # logger.add(
    #     "logs/app.log",
    #     level="INFO",
    #     rotation="10 MB",  # Rotates the log file when it reaches 10 MB
    #     retention="7 days", # Keeps logs for 7 days
    #     compression="zip", # Compresses old log files
    #     format="{time} {level} {message}"
    # )

    return logger


# Create and export the configured logger instance.
# Other modules will import this 'app_logger' to log messages.
app_logger = setup_logger()