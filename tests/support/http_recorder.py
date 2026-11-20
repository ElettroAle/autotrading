"""A local HTTP server that answers 200 to every request and records it: a stand-in for a remote service in tests that
need a real socket, as the OpenTelemetry instrumentation of httpx and the OTLP exporters do.
"""

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


@dataclass(frozen=True, slots=True)
class RecordedRequest:
    method: str
    path: str
    headers: dict[str, str]
    body: bytes


@dataclass(slots=True)
class HttpRecorder:
    address: str
    requests: list[RecordedRequest] = field(default_factory=list)

    def paths(self) -> list[str]:
        return [request.path for request in self.requests]


@contextmanager
def recording_server() -> Iterator[HttpRecorder]:
    recorder = HttpRecorder("")

    class _Recording(BaseHTTPRequestHandler):
        def _record(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length)
            headers = {name.lower(): value for name, value in self.headers.items()}
            recorder.requests.append(RecordedRequest(self.command, self.path, headers, body))
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

        do_GET = _record  # noqa: N815 - the name http.server dispatches to
        do_POST = _record  # noqa: N815 - the name http.server dispatches to

        def log_message(self, format: str, *args: object) -> None:
            """Silent: the test reads the recorded requests, not the log of the server."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Recording)
    host, port = server.server_address[:2]
    recorder.address = f"http://{host!s}:{port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield recorder
    finally:
        server.shutdown()
        server.server_close()
