"""Test fixtures: a fake transport, and Zohal's own published examples.

Nothing here touches the network. Every response body in ``data/openapi_examples.json`` is lifted
verbatim from the examples in Zohal's OpenAPI document, so the record readers are checked against
what Zohal itself says it sends rather than against something written to match the code.

The fake transport replaces the six functions in :mod:`zohal_sdk.common.engine`'s namespace — which
is where the engines resolve them — and records every call, so a test can assert on the payload
that went out as well as on the record that came back.
"""

import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from zohal_sdk import ZohalAsync, ZohalSync
from zohal_sdk.common import engine as engine_module
from zohal_sdk.common.http import RawResponse

TOKEN = "test-token"

#: A card number that satisfies Luhn, an IBAN that satisfies mod-97, and a national code whose
#: check digit holds. Real formats, no real person — the validators reject anything less.
VALID_CARD = "6362141112345674"
VALID_IBAN = "IR820540102680020817909002"
VALID_NATIONAL_CODE = "0013542419"
VALID_NATIONAL_ID = "10103640187"
VALID_MOBILE = "09121234567"
VALID_BIRTH_DATE = "1377/07/19"
VALID_SAYAD_ID = "1234567890123456"
VALID_POSTAL_CODE = "1319733913"


@dataclass
class Call:
    """One request the SDK tried to make."""

    method: str
    url: str
    service: str
    payload: dict[str, Any] | None = None
    files: Mapping[str, Any] | None = None
    fields: Mapping[str, str] | None = None


@dataclass
class FakeTransport:
    """Stands in for ``requests`` and ``aiohttp`` on both engines at once.

    ``queue`` is consumed one response per call; the last one repeats once exhausted, which is what
    lets a polling test hand over ``[pending, pending, completed]`` and then stop.
    """

    queue: list[RawResponse] = field(default_factory=list[RawResponse])
    calls: list[Call] = field(default_factory=list[Call])
    slept: list[float] = field(default_factory=list[float])

    def reply(self, body: dict[str, Any], status: int = 200) -> "FakeTransport":
        self.queue.append(RawResponse(body=body, status=status))
        return self

    def next_response(self) -> RawResponse:
        if not self.queue:
            raise AssertionError("the SDK made a call the test queued no response for")
        return self.queue.pop(0) if len(self.queue) > 1 else self.queue[0]

    @property
    def call(self) -> Call:
        """The only call, asserting that there was exactly one."""
        assert len(self.calls) == 1, f"expected one call, got {len(self.calls)}"
        return self.calls[0]

    @property
    def payload(self) -> dict[str, Any]:
        return self.call.payload or {}


def _install(monkeypatch: pytest.MonkeyPatch, transport: FakeTransport) -> None:
    def post_json(url: str, payload: dict[str, Any], **kw: Any) -> RawResponse:
        transport.calls.append(Call("POST", url, kw["service"], payload=payload))
        return transport.next_response()

    def get_json(url: str, **kw: Any) -> RawResponse:
        transport.calls.append(Call("GET", url, kw["service"]))
        return transport.next_response()

    def post_multipart(url: str, **kw: Any) -> RawResponse:
        transport.calls.append(
            Call("POST", url, kw["service"], files=kw.get("files"), fields=kw.get("fields"))
        )
        return transport.next_response()

    async def apost_json(url: str, payload: dict[str, Any], **kw: Any) -> RawResponse:
        return post_json(url, payload, **kw)

    async def aget_json(url: str, **kw: Any) -> RawResponse:
        return get_json(url, **kw)

    async def apost_multipart(url: str, **kw: Any) -> RawResponse:
        return post_multipart(url, **kw)

    for name, impl in (
        ("post_json", post_json),
        ("get_json", get_json),
        ("post_multipart", post_multipart),
        ("apost_json", apost_json),
        ("aget_json", aget_json),
        ("apost_multipart", apost_multipart),
    ):
        monkeypatch.setattr(engine_module, name, impl)

    # Polling tests must not actually wait. Both sleeps are recorded so a test can assert the
    # interval arithmetic without spending it.
    def sleep(self: Any, seconds: float) -> None:
        transport.slept.append(seconds)

    async def asleep(self: Any, seconds: float) -> None:
        transport.slept.append(seconds)

    monkeypatch.setattr(engine_module.SyncEngine, "_sleep", sleep)
    monkeypatch.setattr(engine_module.AsyncEngine, "_sleep", asleep)


@pytest.fixture
def transport(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeTransport]:
    fake = FakeTransport()
    _install(monkeypatch, fake)
    yield fake


@pytest.fixture
def sync_client(transport: FakeTransport) -> ZohalSync:
    return ZohalSync(token=TOKEN)


@pytest.fixture
def async_client(transport: FakeTransport) -> ZohalAsync:
    return ZohalAsync(token=TOKEN)


@pytest.fixture(scope="session")
def examples() -> dict[str, dict[str, Any]]:
    """Zohal's own published response examples, keyed by path then HTTP status."""
    path = Path(__file__).parent / "data" / "openapi_examples.json"
    data: dict[str, dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    return data


@pytest.fixture
def example(examples: dict[str, dict[str, Any]]) -> Any:
    """``example("/services/inquiry/iban")`` → that endpoint's documented 200 body."""

    def pick(path: str, status: str = "200") -> dict[str, Any]:
        assert path in examples, f"no published example for {path}"
        assert status in examples[path], f"no {status} example for {path}"
        body: dict[str, Any] = examples[path][status]
        return body

    return pick


def envelope(data: Any, *, result: int = 1, message: str = "موفق") -> dict[str, Any]:
    """Build an inquiry envelope by hand, for the cases no published example covers."""
    return {
        "result": result,
        "response_body": {"data": data, "error_code": None, "message": message},
    }
