import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    APP_NAME = os.environ.get("APP_NAME", "CloudPulse")
    APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")
    DATABASE_URL = os.environ.get("DATABASE_URL", "")
    DEBUG = False
    TESTING = False
    JSON_SORT_KEYS = False


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'cloudpulse_dev.db'}"


class TestingConfig(Config):
    """Testing configuration with in-memory or temporary SQLite database."""
    TESTING = True
    DEBUG = True
    DATABASE_URL = "sqlite:///:memory:"


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    # In production, require secure secret key and database URL if provided
    SECRET_KEY = os.environ.get("SECRET_KEY", "prod-secure-random-key-required")
    DATABASE_URL = os.environ.get("DATABASE_URL", "")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config():
    env = os.environ.get("FLASK_ENV", "development").lower()
    return config_by_name.get(env, DevelopmentConfig)
