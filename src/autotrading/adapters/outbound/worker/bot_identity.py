import logging
from collections.abc import Mapping

import httpx

TIMEOUT_SECONDS = 5.0

operations = logging.getLogger("autotrading.notifications")


class WorkerBotIdentityAdapter:
    """The link that opens the platform bot with a link code, asked to the worker, which alone holds the bot token
    (R1.8.1, ADR 0035).

    Without an answer the link-code answer carries no link and the code still works.
    """

    def __init__(self, client: httpx.Client, token: str) -> None:
        self._client = client
        self._token = token

    def start_link(self, code: str) -> str | None:
        try:
            response = self._client.get(
                "/bot/start-link",
                params={"code": code},
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=TIMEOUT_SECONDS,
            )
        except httpx.HTTPError:
            self._record_failure("worker non raggiungibile")
            return None
        if response.status_code != httpx.codes.OK:
            self._record_failure(str(response.status_code))
            return None
        try:
            document = response.json()
        except ValueError:
            return None
        link = document.get("link") if isinstance(document, Mapping) else None
        return link if isinstance(link, str) else None

    def _record_failure(self, cause: str) -> None:
        operations.warning("link del bot non letto dal worker", extra={"cause": cause})
