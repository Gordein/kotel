import pytest

from app import create_app
from app.config import Config


class TestConfig(Config):
    TESTING = True
    DB_PATH = ":memory:"


@pytest.fixture
def app():
    return create_app(TestConfig)


@pytest.fixture
def client(app):
    return app.test_client()
