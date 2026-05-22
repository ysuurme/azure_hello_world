from http.server import BaseHTTPRequestHandler, HTTPServer
from importlib.metadata import PackageNotFoundError, metadata
from typing import Any

from src.config import settings
from src.utils.m_log import f_log, setup_logging


def _identity() -> tuple[str, str]:
    try:
        meta = metadata("my-template-repo")
        return meta["Name"], f"v{meta['Version']}"
    except PackageNotFoundError:
        return "my-template-repo", "v0.0.0"


class HelloHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/":
            name, version = _identity()
            body = f"<html><body><h1>{name} {version}</h1></body></html>".encode()
            self._respond(200, "text/html", body)
        elif self.path == "/healthz":
            self._respond(200, "text/plain", b"ok")
        else:
            self._respond(404, "text/plain", b"Not Found")

    def _respond(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        f_log(f"{self.address_string()} - {format % args}")


def main() -> None:
    setup_logging()
    server = HTTPServer(("0.0.0.0", settings.port), HelloHandler)
    f_log(f"Serving on port {settings.port}", level="start")
    server.serve_forever()


if __name__ == "__main__":
    main()
