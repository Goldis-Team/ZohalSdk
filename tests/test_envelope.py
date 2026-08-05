"""The envelope reader and the error mapping — how a body becomes a record or an exception."""

from typing import Any

import pytest

from tests.conftest import TOKEN, VALID_CARD, FakeTransport, envelope
from zohal_sdk import ZohalSync
from zohal_sdk.common.envelope import read_bare, read_body, read_data, read_lenient
from zohal_sdk.common.exceptions import (
    ZohalAuthenticationError,
    ZohalConfigurationError,
    ZohalNetworkError,
    ZohalServiceError,
)
from zohal_sdk.common.http import decode


class TestEnvelopeShapes:
    def test_inquiry_envelope_yields_the_data_object(self) -> None:
        raw = envelope({"IBAN": "IR82…"})
        assert read_data(raw, status=200, service="x") == {"IBAN": "IR82…"}

    def test_bare_body_envelope_yields_response_body_itself(self) -> None:
        raw = {"result": 1, "response_body": {"session_id": "abc", "status": "pending"}}
        assert read_body(raw, status=200, service="x")["session_id"] == "abc"

    def test_unenveloped_body_passes_straight_through(self) -> None:
        raw = {"reference_id": "abc", "status": "pending"}
        assert read_bare(raw, status=200, service="x") == raw

    def test_unenveloped_body_still_fails_on_a_bad_status(self) -> None:
        # With no `result` to read, the status is all there is to decide on.
        with pytest.raises(ZohalServiceError):
            read_bare({"detail": "nope"}, status=400, service="x")

    def test_lenient_reader_checks_a_result_when_one_is_present(self) -> None:
        with pytest.raises(ZohalServiceError):
            read_lenient(envelope({}, result=6), status=200, service="voice_otp")

    def test_lenient_reader_accepts_a_body_with_no_result_at_all(self) -> None:
        raw = {"sent": True}
        assert read_lenient(raw, status=200, service="voice_otp") == raw

    def test_missing_data_on_a_success_is_empty_not_an_error(self) -> None:
        assert read_data({"result": 1, "response_body": {}}, status=200, service="x") == {}


class TestServiceErrors:
    @pytest.mark.parametrize("status", [200, 400, 404, 500, 503])
    def test_a_non_one_result_raises_under_any_status(self, status: int) -> None:
        # Zohal reports failures in the body; the status alone decides nothing.
        raw = envelope({}, result=6, message="شناسه ملی اشتباه است.")
        with pytest.raises(ZohalServiceError) as caught:
            read_data(raw, status=status, service="company_inquiry")
        assert caught.value.result == 6
        assert caught.value.status == status

    def test_the_exception_carries_zohals_own_message_and_code(self) -> None:
        raw: dict[str, Any] = {
            "result": 6,
            "response_body": {
                "data": {},
                "error_code": "NATIONAL_ID_INVALID",
                "message": "شناسه ملی اشتباه است.",
            },
        }
        with pytest.raises(ZohalServiceError) as caught:
            read_data(raw, status=400, service="company_inquiry")
        error = caught.value
        assert error.error_code == "NATIONAL_ID_INVALID"
        assert "شناسه ملی اشتباه است." in str(error)
        assert error.raw == raw

    def test_the_ocr_endpoints_error_key_is_read_too(self) -> None:
        # That one endpoint spells it `error` rather than `error_code`.
        raw: dict[str, Any] = {
            "result": 5,
            "response_body": {"data": {}, "error": "OCR_FAILED", "message": "x"},
        }
        with pytest.raises(ZohalServiceError) as caught:
            read_data(raw, status=200, service="national_card_ocr")
        assert caught.value.error_code == "OCR_FAILED"


class TestTransportErrors:
    @pytest.mark.parametrize("status", [401, 403])
    def test_auth_statuses_raise_before_the_body_is_parsed(self, status: int) -> None:
        # These bodies are the framework's, not Zohal's, and are often not JSON at all.
        with pytest.raises(ZohalAuthenticationError) as caught:
            decode("<html>Forbidden</html>", status, "shahkar")
        assert caught.value.status == status

    def test_the_auth_error_mentions_the_ip_allowlist(self) -> None:
        with pytest.raises(ZohalAuthenticationError, match="IP is registered"):
            decode("", 403, "shahkar")

    def test_non_json_raises_a_network_error_quoting_what_arrived(self) -> None:
        with pytest.raises(ZohalNetworkError, match="non-JSON"):
            decode("<html>502 Bad Gateway</html>", 502, "iban_inquiry")

    def test_a_json_array_is_not_an_acceptable_body(self) -> None:
        with pytest.raises(ZohalNetworkError, match="not an object"):
            decode("[1, 2, 3]", 200, "iban_inquiry")


class TestClientConstruction:
    def test_an_empty_token_fails_at_construction(self) -> None:
        with pytest.raises(ZohalConfigurationError, match="token is required"):
            ZohalSync(token="   ")

    def test_a_non_positive_timeout_fails_at_construction(self) -> None:
        with pytest.raises(ZohalConfigurationError, match="timeout"):
            ZohalSync(token=TOKEN, timeout=0)

    def test_the_token_is_never_read_from_the_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ZOHAL_TOKEN", "leaked-from-the-environment")
        with pytest.raises(ZohalConfigurationError):
            ZohalSync(token="")

    def test_the_base_url_is_overridable_for_a_recording_proxy(
        self, transport: FakeTransport
    ) -> None:
        client = ZohalSync(token=TOKEN, base_url="http://localhost:8080/")
        transport.reply(envelope({"IBAN": "IR82…"}))
        client.card_to_iban(VALID_CARD)
        assert transport.call.url == ("http://localhost:8080/services/inquiry/card_to_iban")
