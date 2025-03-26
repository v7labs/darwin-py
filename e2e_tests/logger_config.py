import logging
from os import environ

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def setup_logger():
    # Create logger
    logger = logging.getLogger("e2e_tests")

    # Get log level from environment variable or default to INFO
    log_level_name = environ.get("E2E_LOG_LEVEL", "INFO").upper()
    try:
        log_level = getattr(logging, log_level_name)
    except AttributeError:
        log_level = logging.INFO
        logger.warning(f"Invalid log level '{log_level_name}'. Defaulting to INFO.")

    logger.setLevel(log_level)

    # Create console handler with the same log level
    ch = logging.StreamHandler()
    ch.setLevel(log_level)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Add formatter to ch
    ch.setFormatter(formatter)

    # Add ch to logger if no handlers exist
    if not logger.handlers:
        logger.addHandler(ch)

    return logger


# Create and configure logger
logger = setup_logger()
