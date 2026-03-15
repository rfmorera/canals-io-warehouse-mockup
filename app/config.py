import logging
import os
import sys

logger = logging.getLogger(__name__)


def load_config():
    """Load and validate configuration from environment variables.

    Returns a dict of config values. Exits with code 1 if any required
    variable is missing.
    """
    config = {}
    missing = []

    # Required
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        missing.append("DATABASE_URL")
    else:
        config["DATABASE_URL"] = database_url

    if missing:
        for var in missing:
            logger.error("Required environment variable '%s' is not set.", var)
        sys.exit(1)

    # Optional with defaults
    try:
        config["APP_PORT"] = int(os.environ.get("APP_PORT", 5000))
    except ValueError:
        logger.error("Environment variable 'APP_PORT' must be an integer.")
        sys.exit(1)

    return config
