"""The two engine bases every service family builds on.

Each family contributes a pair of mixins — ``BankingSyncMixin`` and ``BankingAsyncMixin``, and so
on — and every one of them inherits from :class:`SyncEngine` or :class:`AsyncEngine` here. That is
what makes the flat client possible without giving up the per-family split: ``ZohalSync`` is the
five sync mixins composed together, and each mixin still lives in its own directory beside its own
``constants.py``, ``data.py`` and ``helpers.py``.

The methods below are the only place a family touches the network. Each one pairs a transport from
:mod:`zohal_sdk.common.http` with a reader from :mod:`zohal_sdk.common.envelope`, so a family engine
method is two lines — make the payload, read the answer — and every decision about *what Zohal
said* stays in that family's pure ``helpers.py``, shared by both engines. That sharing is why the
two cannot drift apart: only the transport call differs between them.

The ``_inquiry*`` methods read the inquiry envelope, the ``_session*`` methods read the biometric
one, and ``_bare`` handles the two credit OTP steps that arrive with no envelope at all.
"""

import asyncio
import time
from collections.abc import Mapping
from typing import Any, NamedTuple

from zohal_sdk.common.constants import BASE_URL, DEFAULT_TIMEOUT
from zohal_sdk.common.data import ZohalConfig
from zohal_sdk.common.envelope import read_bare, read_body, read_data, read_lenient
from zohal_sdk.common.exceptions import ZohalConfigurationError
from zohal_sdk.common.http import (
    FileInput,
    aget_json,
    apost_json,
    apost_multipart,
    get_json,
    post_json,
    post_multipart,
)
from zohal_sdk.common.utils import as_dict, as_text


class Answer(NamedTuple):
    """What a family engine hands to its reader: the fields, and the whole body behind them.

    ``raw`` travels alongside ``data`` all the way into the record so that
    :attr:`~zohal_sdk.common.data.InquiryRecord.raw` holds Zohal's response exactly as it arrived —
    which is what a support ticket needs, and what makes a field this SDK has not modelled still
    reachable.
    """

    data: dict[str, Any]
    raw: dict[str, Any]

    @property
    def message(self) -> str | None:
        """Zohal's message for this answer, which sits one level above ``data`` in the envelope.

        Every record carries it, so reading it here rather than in each family's ``helpers.py``
        is what stops five identical private functions existing. ``None`` for the envelope shapes
        that have no message field at all.
        """
        return as_text(as_dict(self.raw.get("response_body")).get("message"))


def next_poll_delay(interval: float, started: float, now: float, timeout: float) -> float | None:
    """How long a ``wait_for_*`` helper should sleep before asking again, or ``None`` when the
    budget is spent.

    Shared by the biometric and credit pollers, and by both engines, so "have we waited long
    enough" is decided once rather than four times. Never sleeps past the deadline: a 5-second
    interval against 2 seconds of remaining budget waits the 2 seconds and then gives up.
    """
    remaining = timeout - (now - started)
    if remaining <= 0:
        return None
    return min(interval, remaining)


def _build_config(token: str, base_url: str, timeout: float) -> ZohalConfig:
    """Validate at construction, so a misconfigured client fails while you are wiring it up.

    Credentials are constructor arguments and never read from the environment — a client carries
    exactly one token, and one that silently picked up ``ZOHAL_TOKEN`` would bill whichever account
    happened to be exported.
    """
    cleaned = str(token or "").strip()
    if not cleaned:
        raise ZohalConfigurationError(
            "a zohal API token is required — take one from توسعه‌دهندگان → توکن on your panel"
        )
    if timeout <= 0:
        raise ZohalConfigurationError(f"timeout must be positive; got {timeout!r}")
    return ZohalConfig(
        token=cleaned, base_url=str(base_url or BASE_URL).rstrip("/"), timeout=timeout
    )


class SyncEngine:
    """Transport and envelope handling for the sync engine — scripts, Django, Celery workers."""

    def __init__(
        self,
        token: str,
        *,
        base_url: str = BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.config = _build_config(token, base_url, timeout)

    def _url(self, path: str) -> str:
        return f"{self.config.base_url}{path}"

    def _sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    @staticmethod
    def _now() -> float:
        return time.monotonic()

    def _inquiry(self, path: str, payload: dict[str, Any], *, service: str) -> Answer:
        response = post_json(
            self._url(path),
            payload,
            token=self.config.token,
            service=service,
            timeout=self.config.timeout,
        )
        return Answer(
            read_data(response.body, status=response.status, service=service), response.body
        )

    def _inquiry_get(self, path: str, *, service: str) -> Answer:
        response = get_json(
            self._url(path),
            token=self.config.token,
            service=service,
            timeout=self.config.timeout,
        )
        return Answer(
            read_data(response.body, status=response.status, service=service), response.body
        )

    def _inquiry_upload(
        self,
        path: str,
        *,
        files: Mapping[str, FileInput],
        service: str,
        fields: Mapping[str, str] | None = None,
    ) -> Answer:
        response = post_multipart(
            self._url(path),
            files=files,
            fields=fields,
            token=self.config.token,
            service=service,
            timeout=self.config.timeout,
        )
        return Answer(
            read_data(response.body, status=response.status, service=service), response.body
        )

    def _session(self, path: str, payload: dict[str, Any], *, service: str) -> Answer:
        response = post_json(
            self._url(path),
            payload,
            token=self.config.token,
            service=service,
            timeout=self.config.timeout,
        )
        return Answer(
            read_body(response.body, status=response.status, service=service), response.body
        )

    def _session_get(self, path: str, *, service: str) -> Answer:
        response = get_json(
            self._url(path),
            token=self.config.token,
            service=service,
            timeout=self.config.timeout,
        )
        return Answer(
            read_body(response.body, status=response.status, service=service), response.body
        )

    def _session_upload(
        self,
        path: str,
        *,
        files: Mapping[str, FileInput],
        service: str,
        fields: Mapping[str, str] | None = None,
    ) -> Answer:
        response = post_multipart(
            self._url(path),
            files=files,
            fields=fields,
            token=self.config.token,
            service=service,
            timeout=self.config.timeout,
        )
        return Answer(
            read_body(response.body, status=response.status, service=service), response.body
        )

    def _lenient(self, path: str, payload: dict[str, Any], *, service: str) -> Answer:
        response = post_json(
            self._url(path),
            payload,
            token=self.config.token,
            service=service,
            timeout=self.config.timeout,
        )
        return Answer(
            read_lenient(response.body, status=response.status, service=service), response.body
        )

    def _bare(self, path: str, payload: dict[str, Any], *, service: str) -> dict[str, Any]:
        response = post_json(
            self._url(path),
            payload,
            token=self.config.token,
            service=service,
            timeout=self.config.timeout,
        )
        return read_bare(response.body, status=response.status, service=service)


class AsyncEngine:
    """Transport and envelope handling for the async engine — FastAPI, aiohttp, anything on
    asyncio. Every method mirrors :class:`SyncEngine`, awaited."""

    def __init__(
        self,
        token: str,
        *,
        base_url: str = BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.config = _build_config(token, base_url, timeout)

    def _url(self, path: str) -> str:
        return f"{self.config.base_url}{path}"

    async def _sleep(self, seconds: float) -> None:
        # asyncio.sleep, never time.sleep: a polling helper that blocked here would hold the event
        # loop for the whole wait, stalling every other request in the process.
        await asyncio.sleep(seconds)

    @staticmethod
    def _now() -> float:
        return time.monotonic()

    async def _inquiry(self, path: str, payload: dict[str, Any], *, service: str) -> Answer:
        response = await apost_json(
            self._url(path),
            payload,
            token=self.config.token,
            service=service,
            timeout=self.config.timeout,
        )
        return Answer(
            read_data(response.body, status=response.status, service=service), response.body
        )

    async def _inquiry_get(self, path: str, *, service: str) -> Answer:
        response = await aget_json(
            self._url(path),
            token=self.config.token,
            service=service,
            timeout=self.config.timeout,
        )
        return Answer(
            read_data(response.body, status=response.status, service=service), response.body
        )

    async def _inquiry_upload(
        self,
        path: str,
        *,
        files: Mapping[str, FileInput],
        service: str,
        fields: Mapping[str, str] | None = None,
    ) -> Answer:
        response = await apost_multipart(
            self._url(path),
            files=files,
            fields=fields,
            token=self.config.token,
            service=service,
            timeout=self.config.timeout,
        )
        return Answer(
            read_data(response.body, status=response.status, service=service), response.body
        )

    async def _session(self, path: str, payload: dict[str, Any], *, service: str) -> Answer:
        response = await apost_json(
            self._url(path),
            payload,
            token=self.config.token,
            service=service,
            timeout=self.config.timeout,
        )
        return Answer(
            read_body(response.body, status=response.status, service=service), response.body
        )

    async def _session_get(self, path: str, *, service: str) -> Answer:
        response = await aget_json(
            self._url(path),
            token=self.config.token,
            service=service,
            timeout=self.config.timeout,
        )
        return Answer(
            read_body(response.body, status=response.status, service=service), response.body
        )

    async def _session_upload(
        self,
        path: str,
        *,
        files: Mapping[str, FileInput],
        service: str,
        fields: Mapping[str, str] | None = None,
    ) -> Answer:
        response = await apost_multipart(
            self._url(path),
            files=files,
            fields=fields,
            token=self.config.token,
            service=service,
            timeout=self.config.timeout,
        )
        return Answer(
            read_body(response.body, status=response.status, service=service), response.body
        )

    async def _lenient(self, path: str, payload: dict[str, Any], *, service: str) -> Answer:
        response = await apost_json(
            self._url(path),
            payload,
            token=self.config.token,
            service=service,
            timeout=self.config.timeout,
        )
        return Answer(
            read_lenient(response.body, status=response.status, service=service), response.body
        )

    async def _bare(self, path: str, payload: dict[str, Any], *, service: str) -> dict[str, Any]:
        response = await apost_json(
            self._url(path),
            payload,
            token=self.config.token,
            service=service,
            timeout=self.config.timeout,
        )
        return read_bare(response.body, status=response.status, service=service)
