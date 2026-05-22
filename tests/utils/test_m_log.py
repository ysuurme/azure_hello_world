import logging

import pytest

from src.utils.m_log import (
    STAGE,
    STAGE_EMOJI,
    LogLevel,
    _logger,
    f_log,
    f_log_calls,
    f_log_execution,
    setup_logging,
)


@pytest.fixture(autouse=True)
def reset_logging_state():
    """Reset module-level logging state between tests."""
    import src.utils.m_log as m

    m._is_configured = False
    _logger.handlers.clear()
    yield
    m._is_configured = False
    _logger.handlers.clear()


def test_setup_logging_configures_handlers():
    setup_logging(profile="TEST")
    assert len(_logger.handlers) >= 2  # console + file


def test_setup_logging_idempotent():
    setup_logging(profile="TEST")
    handler_count = len(_logger.handlers)
    setup_logging(profile="TEST")
    assert len(_logger.handlers) == handler_count


def test_f_log_info(caplog):
    setup_logging(profile="TEST")
    with caplog.at_level(logging.INFO, logger="app"):
        f_log("hello world")
    assert "hello world" in caplog.text


def test_f_log_stage_emoji(caplog):
    setup_logging(profile="TEST")
    with caplog.at_level(STAGE, logger="app"):
        f_log("pipeline started", level="start")
    assert STAGE_EMOJI[LogLevel.START] in caplog.text


def test_f_log_raises_on_error():
    setup_logging(profile="TEST")
    with pytest.raises(Exception, match="boom"):
        f_log("boom", level="error", raise_exc=True)


def test_f_log_calls_decorator():
    setup_logging(profile="TEST")

    @f_log_calls()
    def my_func():
        return 42

    assert my_func() == 42


def test_f_log_execution_timing(caplog):
    setup_logging(profile="TEST")
    with caplog.at_level(logging.INFO, logger="app"):
        f_log_execution("testproject", start=True)
        f_log_execution("testproject", start=False)
    assert "testproject" in caplog.text.lower()
    assert "execution time" in caplog.text
