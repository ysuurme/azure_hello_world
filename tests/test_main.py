"""Tests for src/main.py."""

import threading
from http.server import HTTPServer
from importlib.metadata import PackageNotFoundError
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from src.main import HelloHandler


@pytest.fixture(scope="module")
def live_server():
    server = HTTPServer(("127.0.0.1", 0), HelloHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield server, port
    server.shutdown()


def test_root_returns_200_with_name(live_server: tuple[HTTPServer, int]) -> None:
    _, port = live_server
    with urlopen(f"http://127.0.0.1:{port}/") as resp:
        assert resp.status == 200
        body = resp.read().decode()
    assert "my-template-repo" in body


def test_healthz_returns_ok(live_server: tuple[HTTPServer, int]) -> None:
    _, port = live_server
    with urlopen(f"http://127.0.0.1:{port}/healthz") as resp:
        assert resp.status == 200
        body = resp.read().decode()
    assert body == "ok"


def test_unknown_path_returns_404(live_server: tuple[HTTPServer, int]) -> None:
    _, port = live_server
    with pytest.raises(HTTPError) as exc_info:
        urlopen(f"http://127.0.0.1:{port}/unknown")
    assert exc_info.value.code == 404


def test_identity_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.main

    def raise_not_found(pkg: str) -> None:
        raise PackageNotFoundError(pkg)

    monkeypatch.setattr(src.main, "metadata", raise_not_found)
    name, version = src.main._identity()
    assert name == "my-template-repo"
    assert version.startswith("v")
