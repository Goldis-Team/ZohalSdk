"""The transport layer itself — the part the fake transport replaces everywhere else.

These tests drive the real :mod:`zohal_sdk.common.http` functions with ``requests`` and ``aiohttp``
stubbed at their own boundary, so the error mapping, the header, and the upload resolution are
exercised rather than assumed.
"""

from pathlib import Path
from typing import Any, ClassVar

import aiohttp
import pytest
import requests

from zohal_sdk.common.exceptions import ZohalNetworkError
from zohal_sdk.common.http import (
    aget_json,
    apost_json,
    apost_multipart,
    as_upload,
    auth_headers,
    get_json,
    post_json,
    post_multipart,
)

TOKEN = "test-token"
URL = "https://service.zohal.io/api/v0/services/inquiry/iban"
OK_BODY = '{"result": 1, "response_body": {"data": {}, "message": "\\u0645\\u0648\\u0641\\u0642"}}'


class FakeResponse:
    def __init__(self, text: str = OK_BODY, status: int = 200) -> None:
        self.text = text
        self.status_code = status


class TestHeaders:
    def test_the_token_travels_as_a_bearer(self) -> None:
        assert auth_headers("abc") == {"Authorization": "Bearer abc"}


class TestSyncTransport:
    def test_post_sends_json_with_the_token_and_decodes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: dict[str, Any] = {}

        def fake_post(url: str, **kw: Any) -> FakeResponse:
            seen.update(url=url, **kw)
            return FakeResponse()

        monkeypatch.setattr(requests, "post", fake_post)
        answer = post_json(URL, {"iban": "IR82"}, token=TOKEN, service="iban_inquiry")
        assert answer.status == 200
        assert answer.body["result"] == 1
        assert seen["json"] == {"iban": "IR82"}
        assert seen["headers"]["Authorization"] == f"Bearer {TOKEN}"

    def test_get_decodes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_get(url: str, **kw: Any) -> FakeResponse:
            return FakeResponse()

        monkeypatch.setattr(requests, "get", fake_get)
        assert get_json(URL, token=TOKEN, service="credit_result").body["result"] == 1

    def test_a_timeout_becomes_a_network_error_naming_the_budget(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def timeout(url: str, **kw: Any) -> FakeResponse:
            raise requests.Timeout("too slow")

        monkeypatch.setattr(requests, "post", timeout)
        with pytest.raises(ZohalNetworkError, match=r"within 30\.0s"):
            post_json(URL, {}, token=TOKEN, service="iban_inquiry", timeout=30.0)

    def test_a_connection_failure_becomes_a_network_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def refused(url: str, **kw: Any) -> FakeResponse:
            raise requests.ConnectionError("refused")

        monkeypatch.setattr(requests, "get", refused)
        with pytest.raises(ZohalNetworkError, match="request for credit_result failed"):
            get_json(URL, token=TOKEN, service="credit_result")

    def test_multipart_sets_no_content_type_so_the_boundary_survives(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: dict[str, Any] = {}

        def fake_post(url: str, **kw: Any) -> FakeResponse:
            seen.update(kw)
            return FakeResponse()

        monkeypatch.setattr(requests, "post", fake_post)
        post_multipart(
            URL,
            files={"file": b"bytes"},
            fields={"type": "selfie_video"},
            token=TOKEN,
            service="upload_biometric_media",
        )
        assert seen["files"] == {"file": ("file", b"bytes")}
        assert seen["data"] == {"type": "selfie_video"}
        assert "Content-Type" not in seen["headers"]


class TestUploads:
    def test_bytes_pass_through_under_the_field_name(self) -> None:
        assert as_upload("file", b"abc") == ("file", b"abc")

    def test_a_bytearray_is_accepted(self) -> None:
        assert as_upload("file", bytearray(b"abc")) == ("file", b"abc")

    def test_a_path_is_read_and_keeps_its_basename(self, tmp_path: Path) -> None:
        target = tmp_path / "card-front.jpg"
        target.write_bytes(b"jpeg-bytes")
        assert as_upload("national_card_front", str(target)) == ("card-front.jpg", b"jpeg-bytes")

    def test_an_open_file_is_read_and_keeps_its_basename(self, tmp_path: Path) -> None:
        target = tmp_path / "selfie.mp4"
        target.write_bytes(b"mp4-bytes")
        with target.open("rb") as handle:
            assert as_upload("file", handle) == ("selfie.mp4", b"mp4-bytes")

    def test_an_unreadable_path_says_which_field_and_which_path(self, tmp_path: Path) -> None:
        missing = tmp_path / "nope.jpg"
        with pytest.raises(ZohalNetworkError, match="could not read national_card_front"):
            as_upload("national_card_front", str(missing))


class FakeAiohttpResponse:
    def __init__(self, text: str, status: int) -> None:
        self._text = text
        self.status = status

    async def text(self) -> str:
        return self._text

    async def __aenter__(self) -> "FakeAiohttpResponse":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class FakeSession:
    """Stands in for ``aiohttp.ClientSession``, recording what it was asked to send."""

    seen: ClassVar[dict[str, Any]] = {}
    error: ClassVar[Exception | None] = None

    def __init__(self, **kw: Any) -> None:
        pass

    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    def _request(self, method: str, url: str, **kw: Any) -> FakeAiohttpResponse:
        if FakeSession.error is not None:
            raise FakeSession.error
        FakeSession.seen = {"method": method, "url": url, **kw}
        return FakeAiohttpResponse(OK_BODY, 200)

    def post(self, url: str, **kw: Any) -> FakeAiohttpResponse:
        return self._request("POST", url, **kw)

    def get(self, url: str, **kw: Any) -> FakeAiohttpResponse:
        return self._request("GET", url, **kw)


@pytest.fixture
def fake_aiohttp(monkeypatch: pytest.MonkeyPatch) -> type[FakeSession]:
    FakeSession.seen = {}
    FakeSession.error = None
    monkeypatch.setattr(aiohttp, "ClientSession", FakeSession)
    return FakeSession


class TestAsyncTransport:
    async def test_post_sends_json_with_the_token(self, fake_aiohttp: type[FakeSession]) -> None:
        answer = await apost_json(URL, {"iban": "IR82"}, token=TOKEN, service="iban_inquiry")
        assert answer.status == 200
        assert fake_aiohttp.seen["json"] == {"iban": "IR82"}
        assert fake_aiohttp.seen["headers"]["Authorization"] == f"Bearer {TOKEN}"

    async def test_get_decodes(self, fake_aiohttp: type[FakeSession]) -> None:
        answer = await aget_json(URL, token=TOKEN, service="credit_result")
        assert answer.body["result"] == 1
        assert fake_aiohttp.seen["method"] == "GET"

    async def test_multipart_builds_a_form(self, fake_aiohttp: type[FakeSession]) -> None:
        await apost_multipart(
            URL,
            files={"file": b"bytes"},
            fields={"type": "selfie_video"},
            token=TOKEN,
            service="upload_biometric_media",
        )
        assert isinstance(fake_aiohttp.seen["data"], aiohttp.FormData)

    async def test_a_client_error_becomes_a_network_error(
        self, fake_aiohttp: type[FakeSession]
    ) -> None:
        fake_aiohttp.error = aiohttp.ClientError("boom")
        with pytest.raises(ZohalNetworkError, match="request for iban_inquiry failed"):
            await apost_json(URL, {}, token=TOKEN, service="iban_inquiry")

    async def test_a_timeout_becomes_a_network_error(self, fake_aiohttp: type[FakeSession]) -> None:
        fake_aiohttp.error = TimeoutError()
        with pytest.raises(ZohalNetworkError, match=r"within 30\.0s"):
            await aget_json(URL, token=TOKEN, service="credit_result", timeout=30.0)
