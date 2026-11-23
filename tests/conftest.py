import pytest
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.database import DatabaseManager


@pytest.fixture
def app():
    """Create and configure a testing instance of the Flask application."""
    test_config = {
        "TESTING": True,
        "DEBUG": False,
        "DATABASE_URL": "sqlite:///:memory:",
        "APP_NAME": "CloudPulse-Test",
        "APP_VERSION": "1.0.0-test"
    }
    application = create_app(config_name="testing", test_config=test_config)
    yield application


@pytest.fixture
def client(app):
    """A test client for the application."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test CLI runner for the application."""
    return app.test_cli_runner()
