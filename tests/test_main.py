"""Tests for src/main.py — FastAPI application endpoints."""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app


def _make_result(text: str, state: dict, status: str, artifacts: dict | None = None) -> MagicMock:
    r = MagicMock()
    r.response_text = text
    r.updated_state = state
    r.artifacts = artifacts or {}
    r.status = status
    return r


@pytest.fixture
def mock_dispatcher() -> MagicMock:
    d = MagicMock()
    d.dispatch.return_value = _make_result("ok", {}, "completed")
    return d


@pytest.fixture
def client(mock_dispatcher: MagicMock):
    with patch("src.main.m_ai_client.ClientManager"):
        with patch("src.main.WorkflowDispatcher", return_value=mock_dispatcher):
            with TestClient(app) as c:
                yield c, mock_dispatcher


class TestHealthz:
    def test_healthz_returns_200(self, client) -> None:
        c, _ = client
        resp = c.get("/healthz")
        assert resp.status_code == 200

    def test_healthz_response_body(self, client) -> None:
        c, _ = client
        assert c.get("/healthz").json() == {"status": "ok"}

    def test_healthz_no_azure_call(self, client) -> None:
        c, d = client
        c.get("/healthz")
        d.dispatch.assert_not_called()


class TestDispatchHelp:
    def test_help_command_returns_200(self, client) -> None:
        c, d = client
        d.dispatch.return_value = _make_result("| Slash Command | Module | Description |", {}, "completed")
        resp = c.post("/dispatch", json={"query": "/help", "session_state": {}})
        assert resp.status_code == 200

    def test_help_command_status_completed(self, client) -> None:
        c, d = client
        d.dispatch.return_value = _make_result("| Slash Command |", {}, "completed")
        resp = c.post("/dispatch", json={"query": "/help", "session_state": {}})
        assert resp.json()["status"] == "completed"

    def test_help_command_forwards_query_to_dispatcher(self, client) -> None:
        c, d = client
        c.post("/dispatch", json={"query": "/help", "session_state": {}})
        d.dispatch.assert_called_once_with("/help", {})


class TestDispatchExit:
    def test_exit_command_returns_200(self, client) -> None:
        c, d = client
        d.dispatch.return_value = _make_result("Session cleared.", {}, "completed")
        resp = c.post("/dispatch", json={"query": "/exit", "session_state": {"active_module": "/diagram"}})
        assert resp.status_code == 200

    def test_exit_forwards_session_state(self, client) -> None:
        c, d = client
        state = {"active_module": "/diagram"}
        c.post("/dispatch", json={"query": "/exit", "session_state": state})
        d.dispatch.assert_called_once_with("/exit", state)


class TestDispatchUnknownCommand:
    def test_unknown_command_returns_200(self, client) -> None:
        c, d = client
        d.dispatch.return_value = _make_result("Unknown command: `/bogus`.", {}, "unknown_command")
        resp = c.post("/dispatch", json={"query": "/bogus", "session_state": {}})
        assert resp.status_code == 200

    def test_unknown_command_status_is_unknown(self, client) -> None:
        c, d = client
        d.dispatch.return_value = _make_result("Unknown command", {}, "unknown_command")
        resp = c.post("/dispatch", json={"query": "/bogus", "session_state": {}})
        assert resp.json()["status"] == "unknown_command"


class TestDispatchResponseContract:
    def test_response_has_required_fields(self, client) -> None:
        c, _ = client
        resp = c.post("/dispatch", json={"query": "/help", "session_state": {}})
        body = resp.json()
        assert "response_text" in body
        assert "updated_state" in body
        assert "artifacts" in body
        assert "status" in body

    def test_artifacts_has_svg_and_d2_fields(self, client) -> None:
        c, _ = client
        resp = c.post("/dispatch", json={"query": "/help", "session_state": {}})
        artifacts = resp.json()["artifacts"]
        assert "svg" in artifacts
        assert "d2" in artifacts

    def test_svg_bytes_are_base64_encoded(self, client) -> None:
        c, d = client
        raw = b"<svg>test</svg>"
        d.dispatch.return_value = _make_result("diagram", {}, "completed", {"svg": raw})
        resp = c.post("/dispatch", json={"query": "/diagram test", "session_state": {}})
        assert resp.json()["artifacts"]["svg"] == base64.b64encode(raw).decode()

    def test_session_state_forwarded_to_dispatcher(self, client) -> None:
        c, d = client
        state = {"active_module": "/diagram", "module_state": {}}
        c.post("/dispatch", json={"query": "my answer", "session_state": state})
        d.dispatch.assert_called_once_with("my answer", state)

    def test_updated_state_returned_from_dispatcher(self, client) -> None:
        c, d = client
        new_state = {"active_module": "/diagram"}
        d.dispatch.return_value = _make_result("ok", new_state, "completed")
        resp = c.post("/dispatch", json={"query": "/diagram test", "session_state": {}})
        assert resp.json()["updated_state"] == new_state
