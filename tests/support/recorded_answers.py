"""Answers of the real services, captured once live and saved as they arrived, for the integration tests of the sources
(ADR fonti-provate-su-risposte-registrate).

Every answer `<name>.<ext>` of `tests/integration/sources/recorded/<technology>/` has its `<name>.recording.json`: the
request that received it (method, URL, JSON body), the status, the content type, where it comes from and when it was
recorded. A request without a recording fails the test: no test of a source reaches the network.
"""

import io
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast, override

import httpx
import pytest
import requests
from hyperliquid.info import Info
from requests.adapters import BaseAdapter

from autotrading.adapters.outbound.hyperliquid.exchange import HyperliquidSdkAdapter
from autotrading.adapters.outbound.hyperliquid.market_metadata import _MarketMetadata, _Metadata

RECORDED = Path(__file__).resolve().parents[1] / "integration" / "sources" / "recorded"
RECORDING_SUFFIX = ".recording.json"


@dataclass(frozen=True, slots=True)
class RecordedAnswer:
    """One answer of a service and the request that received it."""

    method: str
    url: str
    request_body: object
    status: int
    content_type: str
    content: bytes

    def answers(self, method: str, url: str, body: object) -> bool:
        return (self.method, self.url, self.request_body) == (method, url, body)


def recorded_answer(technology: str, name: str) -> RecordedAnswer:
    folder = RECORDED / technology
    recording = cast("Mapping[str, object]", json.loads((folder / f"{name}{RECORDING_SUFFIX}").read_text("utf-8")))
    return RecordedAnswer(
        str(recording["method"]),
        str(recording["url"]),
        recording["request_body"],
        int(str(recording["status"])),
        str(recording["content_type"]),
        (folder / str(recording["answer"])).read_bytes(),
    )


class RecordedService:
    """Answers every request with the recorded answer of its method, URL and body, or with one recorded error, and keeps
    the requests it received."""

    def __init__(self, technology: str, *names: str, error: str | None = None) -> None:
        self._answers = [recorded_answer(technology, name) for name in names]
        self._error = None if error is None else recorded_answer(technology, error)
        self.received: list[tuple[str, str, object]] = []

    def answer_of(self, method: str, url: str, body: object) -> RecordedAnswer:
        self.received.append((method, url, body))
        if self._error is not None:
            return self._error
        answer = next((answer for answer in self._answers if answer.answers(method, url, body)), None)
        if answer is None:
            pytest.fail(f"no recorded answer for {method} {url} {body!r}: a test of a source never reaches the network")
        return answer


class RecordedHttpxService(RecordedService):
    """The recorded service behind an httpx.MockTransport, for the adapters that receive an httpx.Client."""

    def __init__(self, technology: str, *names: str, error: str | None = None) -> None:
        super().__init__(technology, *names, error=error)
        self.requests: list[httpx.Request] = []

    def client(self, base_url: str = "") -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self._handle), base_url=base_url)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        answer = self.answer_of(request.method, str(request.url), None)
        return httpx.Response(answer.status, headers={"content-type": answer.content_type}, content=answer.content)


class RecordedInfoTransport(BaseAdapter):
    """The recorded info endpoint of Hyperliquid as a transport of the requests session of the official SDK."""

    def __init__(self, service: RecordedService) -> None:
        super().__init__()
        self._service = service

    @override
    def send(
        self,
        request: requests.PreparedRequest,
        stream: bool = False,
        timeout: float | tuple[float | None, float | None] | None = None,
        verify: bool | str = True,
        cert: bytes | str | tuple[bytes | str, bytes | str] | None = None,
        proxies: Mapping[str, str] | None = None,
    ) -> requests.Response:
        body: object = json.loads(request.body if isinstance(request.body, bytes | str) else b"null")
        answer = self._service.answer_of(str(request.method), str(request.url), body)
        response = requests.Response()
        response.status_code = answer.status
        response.headers["Content-Type"] = answer.content_type
        response.raw = io.BytesIO(answer.content)
        response.url = str(request.url)
        response.request = request
        return response

    @override
    def close(self) -> None:
        """Nothing to release: no connection is ever opened."""


def _answered_by_the_recordings(info: Info, service: RecordedService) -> Info:
    transport = RecordedInfoTransport(service)
    info.session.mount("https://", transport)
    info.session.mount("http://", transport)
    return info


class _RecordedMarketMetadata(_MarketMetadata):
    """Reads the market metadata, as the SDK asks them, from the recorded info endpoint."""

    def __init__(self, service: RecordedService) -> None:
        self._service = service

    @override
    def of(self, base_url: str, timeout: float) -> _Metadata:
        # Empty metadata only spare the client its own download: it reads the recorded ones right after.
        info = Info(
            base_url, skip_ws=True, meta={"universe": []}, spot_meta={"universe": [], "tokens": []}, timeout=timeout
        )
        recorded = _answered_by_the_recordings(info, self._service)
        return _Metadata(recorded.meta(), recorded.spot_meta())


class RecordedInfoSdk(HyperliquidSdkAdapter):
    """The official SDK whose every info client is answered by the recorded info endpoint of the testnet."""

    def __init__(self, service: RecordedService) -> None:
        super().__init__(_RecordedMarketMetadata(service))
        self._service = service

    @override
    def info(self, base_url: str, timeout: float) -> Info:
        return _answered_by_the_recordings(super().info(base_url, timeout), self._service)
