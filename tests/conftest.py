import pytest

import src.utils.m_log as m_log


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging state between every test to prevent handler accumulation."""
    import logging

    m_log._is_configured = False
    m_log._logger.handlers.clear()
    logging.root.handlers.clear()
    yield
    m_log._is_configured = False
    m_log._logger.handlers.clear()
    logging.root.handlers.clear()


@pytest.fixture
def mock_settings(monkeypatch):
    """Override settings for tests — prevents reading .env from disk."""
    monkeypatch.setattr("src.config.settings.log_profile", "TEST")
    monkeypatch.setattr("src.config.settings.google_api_key", "test-key")
