"""Video identity verification (احراز هویت ویدیویی) — the bare-body envelope, and polling."""

from collections.abc import Callable
from typing import Any

import pytest

from tests.conftest import VALID_BIRTH_DATE, VALID_NATIONAL_CODE, FakeTransport
from zohal_sdk import ZohalSync
from zohal_sdk.common.exceptions import ZohalPollTimeoutError

Example = Callable[..., dict[str, Any]]

SESSION_ID = "0f3a5c1e-1111-2222-3333-444455556666"
VIDEO_ID = "a271d113-10f1-4633-8180-890e6cef84cc"


def result_body(
    status: str, result: str | None = None, reason: str | None = None
) -> dict[str, Any]:
    """The biometric endpoints answer with `response_body` as the payload — no `data` wrapper."""
    return {
        "result": 1,
        "response_body": {
            "status": status,
            "result": result,
            "reason": reason,
            "type": "liveness",
            "completed_at": None,
        },
    }


class TestUpload:
    def test_media_upload_reads_the_bare_body(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/biometric/media/"))
        record = sync_client.upload_biometric_media(b"video-bytes")
        assert record.id == "<UUID>"
        assert record.type == "selfie_video"

    def test_the_media_type_travels_as_a_form_field(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/biometric/media/"))
        sync_client.upload_biometric_media(b"video-bytes")
        assert transport.call.fields == {"type": "selfie_video"}
        assert transport.call.files is not None
        assert set(transport.call.files) == {"file"}


class TestLivenessSession:
    def test_opening_a_session(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/biometric/session/liveness/"))
        record = sync_client.start_liveness(
            VALID_NATIONAL_CODE, VALID_BIRTH_DATE, "1G34567890", VIDEO_ID
        )
        assert record.session_id == "<UUID>"
        assert record.status == "pending"

    def test_the_video_is_referenced_by_id_not_sent_inline(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/biometric/session/liveness/"))
        sync_client.start_liveness(VALID_NATIONAL_CODE, VALID_BIRTH_DATE, "1G34567890", VIDEO_ID)
        assert transport.payload["media"] == {"selfie_video": VIDEO_ID}

    def test_the_callback_url_is_omitted_unless_given(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/biometric/session/liveness/"))
        sync_client.start_liveness(VALID_NATIONAL_CODE, VALID_BIRTH_DATE, "1G34567890", VIDEO_ID)
        assert "callback_url" not in transport.payload

    def test_the_callback_url_is_sent_when_given(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/biometric/session/liveness/"))
        sync_client.start_liveness(
            VALID_NATIONAL_CODE,
            VALID_BIRTH_DATE,
            "1G34567890",
            VIDEO_ID,
            callback_url="https://example.test/hook",
        )
        assert transport.payload["callback_url"] == "https://example.test/hook"


class TestResult:
    def test_a_matched_session_is_truthy(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/biometric/session/{id}/result"))
        record = sync_client.biometric_result(SESSION_ID)
        assert record.result == "matched"
        assert record.reason == "ACCEPT"
        assert record.matched
        assert record

    def test_a_pending_session_is_falsy_and_not_final(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        transport.reply(result_body("pending"))
        record = sync_client.biometric_result(SESSION_ID)
        assert not record
        assert not record.is_final

    def test_a_completed_but_unmatched_session_is_final_and_falsy(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        transport.reply(result_body("completed", "not_matched", "REJECT"))
        record = sync_client.biometric_result(SESSION_ID)
        assert record.is_final
        assert not record

    def test_the_session_id_is_carried_over_since_zohal_omits_it(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        transport.reply(result_body("pending"))
        assert sync_client.biometric_result(SESSION_ID).session_id == SESSION_ID

    def test_the_id_is_interpolated_into_the_path(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        transport.reply(result_body("pending"))
        sync_client.biometric_result(SESSION_ID)
        assert transport.call.url.endswith(f"/services/biometric/session/{SESSION_ID}/result")
        assert transport.call.method == "GET"


class TestPolling:
    def test_it_returns_as_soon_as_the_session_is_final(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        transport.reply(result_body("pending"))
        transport.reply(result_body("pending"))
        transport.reply(result_body("completed", "matched", "ACCEPT"))
        record = sync_client.wait_for_biometric_result(SESSION_ID, timeout=60, interval=3)
        assert record.matched
        assert len(transport.calls) == 3
        assert transport.slept == [3, 3]

    def test_it_does_not_sleep_at_all_when_the_first_answer_is_final(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        transport.reply(result_body("completed", "matched", "ACCEPT"))
        sync_client.wait_for_biometric_result(SESSION_ID)
        assert transport.slept == []

    def test_a_failed_session_is_terminal_and_is_not_polled_to_the_timeout(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        transport.reply(result_body("failed", None, "BAD_VIDEO"))
        record = sync_client.wait_for_biometric_result(SESSION_ID, timeout=60)
        assert record.status == "failed"
        assert len(transport.calls) == 1

    def test_it_raises_once_the_budget_is_spent(
        self, sync_client: ZohalSync, transport: FakeTransport, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ticks = iter([0.0, 10.0, 20.0, 30.0, 40.0])
        monkeypatch.setattr(type(sync_client), "_now", staticmethod(lambda: next(ticks)))
        transport.reply(result_body("pending"))
        with pytest.raises(ZohalPollTimeoutError) as caught:
            sync_client.wait_for_biometric_result(SESSION_ID, timeout=15, interval=10)
        assert caught.value.reference == SESSION_ID
        assert caught.value.last_status == "pending"

    def test_it_never_sleeps_past_the_deadline(
        self, sync_client: ZohalSync, transport: FakeTransport, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # 10s budget, 8s already elapsed, 5s interval → wait the 2s that remain, not 5.
        ticks = iter([0.0, 8.0, 10.0])
        monkeypatch.setattr(type(sync_client), "_now", staticmethod(lambda: next(ticks)))
        transport.reply(result_body("pending"))
        with pytest.raises(ZohalPollTimeoutError):
            sync_client.wait_for_biometric_result(SESSION_ID, timeout=10, interval=5)
        assert transport.slept == [2.0]
