"""An httpx client answered by an ASGI application in memory, for the adapters that speak httpx.

Starlette's TestClient speaks httpx2 once the OpenAI SDK installs it: the bridge keeps the adapters under test on
the client type they receive in production.
"""

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

# The test client already decoded the body: the bridge must not ask httpx to decode it again.
DECODED_HEADERS = frozenset({"content-encoding", "content-length", "transfer-encoding"})


def served_in_memory(application: FastAPI) -> httpx.Client:
    test_client = TestClient(application)

    def forward(request: httpx.Request) -> httpx.Response:
        answer = test_client.request(
            request.method, str(request.url), content=request.content, headers=dict(request.headers)
        )
        headers = [(name, value) for name, value in answer.headers.multi_items() if name.lower() not in DECODED_HEADERS]
        return httpx.Response(answer.status_code, headers=headers, content=answer.content)

    return httpx.Client(transport=httpx.MockTransport(forward), base_url=str(test_client.base_url))
