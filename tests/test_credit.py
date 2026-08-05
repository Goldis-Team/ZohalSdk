"""Credit scoring (استعلام اعتبارسنجی) — the unenveloped OTP steps, and the deep report."""

from collections.abc import Callable
from typing import Any

import pytest

from tests.conftest import VALID_MOBILE, VALID_NATIONAL_CODE, FakeTransport, envelope
from zohal_sdk import ZohalSync
from zohal_sdk.common.exceptions import ZohalPollTimeoutError, ZohalServiceError

Example = Callable[..., dict[str, Any]]

REFERENCE_ID = "69061561dXXXXXXXX10fb63e"


class TestOtpSteps:
    def test_send_otp_reads_an_unenveloped_body(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        # This step answers {reference_id, status} at the top level, with no `result` at all.
        transport.reply(example("/services/inquiry/credit_inquiry/send_otp"))
        record = sync_client.credit_send_otp(VALID_NATIONAL_CODE, VALID_MOBILE)
        assert record.reference_id == "<<ID>>"
        assert record.status == "pending"

    def test_send_otp_fails_on_a_bad_status_since_there_is_no_result_to_read(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        transport.reply({"detail": "rate limited"}, status=429)
        with pytest.raises(ZohalServiceError) as caught:
            sync_client.credit_send_otp(VALID_NATIONAL_CODE, VALID_MOBILE)
        assert caught.value.status == 429

    def test_verify_otp_accepts_an_undocumented_response(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        transport.reply({"status": "verified"})
        record = sync_client.credit_verify_otp(REFERENCE_ID, "55555")
        assert record.status == "verified"
        assert record.reference_id == REFERENCE_ID

    def test_verify_otp_carries_the_reference_when_zohal_omits_it(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        transport.reply({})
        assert sync_client.credit_verify_otp(REFERENCE_ID, "55555").reference_id == REFERENCE_ID


class TestReport:
    @pytest.fixture
    def report(self, sync_client: ZohalSync, transport: FakeTransport, example: Example) -> Any:
        transport.reply(example("/services/inquiry/credit_inquiry/result/{reference_id}"))
        return sync_client.credit_result(REFERENCE_ID)

    def test_it_is_truthy_once_completed(self, report: Any) -> None:
        assert report.status == "completed"
        assert report.is_final
        assert report

    def test_personal_information(self, report: Any) -> None:
        assert report.personal_information is not None
        assert report.personal_information.first_name == "علی"
        assert report.personal_information.last_name == "علیپور"
        assert report.personal_information.has_blocked_contract is True

    def test_the_score_and_its_reasons(self, report: Any) -> None:
        assert report.score is not None
        assert report.score.score == 555
        assert report.score.risk == "C2"
        assert report.score.description == "ریسک متوسط"
        assert report.score.codes[0].code == "NGS1"

    def test_direct_contracts_are_read_in_full(self, report: Any) -> None:
        contract = report.direct_contracts[0]
        assert contract.organization_name == "بانک پاسارگاد"
        assert contract.customer_role_title == "متقاضی اصلی"
        assert contract.total_amount == 1000
        assert contract.instalment_amount == 10000
        assert contract.phase_of_operation_title == "خاتمه یافته به درخواست مشتری"

    def test_a_contracts_repayment_history(self, report: Any) -> None:
        contract = report.direct_contracts[0]
        assert len(contract.repayments) == 12
        assert contract.repayments[0].negative_contract_status == 0

    def test_undocumented_contract_collections_pass_through_empty(self, report: Any) -> None:
        contract = report.direct_contracts[0]
        assert contract.guarantees == ()
        assert contract.related_persons == ()

    def test_the_sections_report_their_own_upstream_status(self, report: Any) -> None:
        assert report.judiciary is not None
        assert report.judiciary.status == 200
        assert report.judiciary.answered
        assert report.pichak is not None
        assert report.pichak.answered
        assert report.tax is not None
        assert report.tax.answered

    def test_a_404_from_the_cheque_registry_is_an_answer_not_a_failure(self, report: Any) -> None:
        # No returned cheques on file is exactly what a 404 here means.
        assert report.bounced_cheque is not None
        assert report.bounced_cheque.status == 404
        assert not report.bounced_cheque.answered
        assert report.bounced_cheque.cheques == ()

    def test_judiciary_data(self, report: Any) -> None:
        assert report.judiciary.data is not None
        assert report.judiciary.data.bankruptcy_count == 0
        assert report.judiciary.data.sum_not_execute_count == 0

    def test_pichak_cheque_counts(self, report: Any) -> None:
        assert report.pichak.data is not None
        titles = [item.check_status_title for item in report.pichak.data.items]
        assert "برگشتی" in titles
        assert report.pichak.data.sum_count == 0

    def test_tax_years(self, report: Any) -> None:
        assert report.tax.years
        assert report.tax.years[0].year == 1404

    def test_inquiry_history_and_roles(self, report: Any) -> None:
        assert report.inquiry_histories[0].bank_name == "بانک پاسارگاد"
        assert report.person_roles[0].number_of_contracts is not None

    def test_total_overdue_sums_direct_contracts_only(self, report: Any) -> None:
        assert report.total_overdue == sum(c.overdue_amount or 0 for c in report.direct_contracts)

    def test_a_pending_report_has_empty_sections_and_is_falsy(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        transport.reply(envelope({"reference_id": REFERENCE_ID, "status": "pending"}))
        record = sync_client.credit_result(REFERENCE_ID)
        assert not record
        assert not record.is_final
        assert record.personal_information is None
        assert record.direct_contracts == ()

    def test_the_reference_is_interpolated_into_the_path(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        transport.reply(envelope({"status": "pending"}))
        sync_client.credit_result(REFERENCE_ID)
        assert transport.call.url.endswith(
            f"/services/inquiry/credit_inquiry/result/{REFERENCE_ID}"
        )
        assert transport.call.method == "GET"


class TestPolling:
    def test_it_returns_once_the_report_completes(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(envelope({"status": "pending"}))
        transport.reply(example("/services/inquiry/credit_inquiry/result/{reference_id}"))
        report = sync_client.wait_for_credit_result(REFERENCE_ID, timeout=60, interval=5)
        assert report.is_completed
        assert len(transport.calls) == 2
        assert transport.slept == [5]

    def test_it_raises_once_the_budget_is_spent(
        self, sync_client: ZohalSync, transport: FakeTransport, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ticks = iter([0.0, 100.0, 200.0])
        monkeypatch.setattr(type(sync_client), "_now", staticmethod(lambda: next(ticks)))
        transport.reply(envelope({"status": "pending"}))
        with pytest.raises(ZohalPollTimeoutError) as caught:
            sync_client.wait_for_credit_result(REFERENCE_ID, timeout=60)
        assert caught.value.reference == REFERENCE_ID
        assert caught.value.last_status == "pending"
