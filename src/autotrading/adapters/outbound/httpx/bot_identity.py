import logging
from collections.abc import Mapping

import httpx

from autotrading.adapters.outbound.httpx.telegram import START_LINK

TIMEOUT_SECONDS = 5.0

operations = logging.getLogger("autotrading.notifications")


class HttpxWorkerBotIdentityAdapter:
    """The username of the platform bot, asked to the worker, which alone holds the bot token (R1.8.1, ADR 0035).

    A known username is kept; without it the link-code answer carries no link and the code still works.
    """

    def __init__(self, client: httpx.Client, token: str) -> None:
        self._client = client
        self._token = token
        self._username: str | None = None

    def username(self) -> str | None:
        if self._username is None:
            self._username = self._read()
        return self._username

    def start_link(self, code: str) -> str | None:
        username = self.username()
        return None if username is None else START_LINK.format(bot=username, code=code)

    def _read(self) -> str | None:
        try:
            response = self._client.get(
                "/bot", headers={"Authorization": f"Bearer {self._token}"}, timeout=TIMEOUT_SECONDS
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
        username = document.get("username") if isinstance(document, Mapping) else None
        return username if isinstance(username, str) else None

    def _record_failure(self, cause: str) -> None:
        operations.warning("nome del bot non letto dal worker", extra={"cause": cause})
