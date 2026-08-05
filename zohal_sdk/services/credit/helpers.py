"""Credit scoring (استعلام اعتبارسنجی) — payload building and response reading.

Pure functions, called by both engines. The bulk of this module is reading the report: one
``_read_*`` per section, each tolerant of a section its upstream did not answer.
"""

from typing import Any

from zohal_sdk.common.engine import Answer
from zohal_sdk.common.utils import (
    as_bool,
    as_dict,
    as_dicts,
    as_int,
    as_text,
    check_mobile,
    check_national_code,
    check_required,
)
from zohal_sdk.services.credit.constants import RESULT
from zohal_sdk.services.credit.data import (
    BouncedChequeSection,
    ChequeStatusCount,
    ContractSummary,
    CreditContract,
    CreditOtpRequest,
    CreditOtpVerification,
    CreditReport,
    CreditScore,
    InquiryHistory,
    InquiryStats,
    JudiciaryData,
    JudiciarySection,
    NegativeStatus,
    PersonalInformation,
    PersonRole,
    PichakData,
    PichakSection,
    Repayment,
    ScoreCode,
    TaxSection,
    TaxYear,
)


def send_otp_payload(national_code: str, mobile: str) -> dict[str, Any]:
    return {
        "national_code": check_national_code(national_code),
        "mobile": check_mobile(mobile),
    }


def verify_otp_payload(reference_id: str, otp: str) -> dict[str, Any]:
    return {
        "reference_id": check_required(reference_id, field="reference_id", label="reference id"),
        "otp": check_required(otp, field="otp", label="OTP code"),
    }


def result_path(reference_id: str) -> str:
    return RESULT.format(
        reference_id=check_required(reference_id, field="reference_id", label="reference id")
    )


def read_otp_request(raw: dict[str, Any]) -> CreditOtpRequest:
    """This step answers with a bare body — no envelope, so no ``message`` to read."""
    return CreditOtpRequest(
        reference_id=as_text(raw.get("reference_id")),
        status=as_text(raw.get("status")),
        raw=raw,
    )


def read_otp_verification(raw: dict[str, Any], reference_id: str) -> CreditOtpVerification:
    return CreditOtpVerification(
        # Zohal's undocumented response may or may not echo the reference; the one from the request
        # is used when it does not, so the record can always say which flow it belongs to.
        reference_id=as_text(raw.get("reference_id")) or reference_id,
        status=as_text(raw.get("status")),
        data=raw,
        raw=raw,
    )


def _read_personal(raw: dict[str, Any]) -> PersonalInformation | None:
    if not raw:
        return None
    return PersonalInformation(
        national_code=as_text(raw.get("national_code")),
        first_name=as_text(raw.get("first_name")),
        last_name=as_text(raw.get("last_name")),
        father_name=as_text(raw.get("father_name")),
        birth_date=as_text(raw.get("birth_date")),
        gender=as_text(raw.get("gender")),
        marital_status=as_text(raw.get("marital_status")),
        has_blocked_contract=as_bool(raw.get("has_blocked_contract")),
    )


def _read_score(raw: dict[str, Any]) -> CreditScore | None:
    if not raw:
        return None
    return CreditScore(
        score=as_int(raw.get("score")),
        risk=as_text(raw.get("risk")),
        description=as_text(raw.get("description")),
        score_type=as_text(raw.get("score_type")),
        inquiry_created_date=as_text(raw.get("inquiry_created_date")),
        previous_score=as_bool(raw.get("previous_score")),
        previous_score_date=as_text(raw.get("previous_score_date")),
        codes=tuple(
            ScoreCode(code=as_text(item.get("code")), description=as_text(item.get("description")))
            for item in as_dicts(raw.get("score_codes"))
        ),
    )


def _read_repayment(raw: dict[str, Any]) -> Repayment:
    return Repayment(
        date=as_text(raw.get("date")),
        negative_contract_status=as_int(raw.get("negative_contract_status")),
        overdue_amount=as_int(raw.get("overdue_amount")),
        total_number_of_overdue=as_int(raw.get("total_number_of_overdue")),
    )


def _read_contract(raw: dict[str, Any]) -> CreditContract:
    return CreditContract(
        contract_id=as_int(raw.get("contract_id")),
        contract_number=as_text(raw.get("contract_number")),
        organization_name=as_text(raw.get("organization_name")),
        organization_name_code=as_text(raw.get("organization_name_code")),
        organization_type=as_text(raw.get("organization_type")),
        organization_type_code=as_text(raw.get("organization_type_code")),
        customer_role=as_int(raw.get("customer_role")),
        customer_role_code=as_text(raw.get("customer_role_code")),
        customer_role_title=as_text(raw.get("customer_role_title")),
        total_amount=as_int(raw.get("total_amount")),
        instalment_amount=as_int(raw.get("instalment_amount")),
        outstanding_amount=as_int(raw.get("outstanding_amount")),
        overdue_amount=as_int(raw.get("overdue_amount")),
        total_number_of_installments=as_int(raw.get("total_number_of_installments")),
        total_number_of_outstanding=as_int(raw.get("total_number_of_outstanding")),
        total_number_of_overdue=as_int(raw.get("total_number_of_overdue")),
        negative_contract_status=as_text(raw.get("negative_contract_status")),
        negative_contract_status_code=as_text(raw.get("negative_contract_status_code")),
        phase_of_operation=as_int(raw.get("phase_of_operation")),
        phase_of_operation_code=as_text(raw.get("phase_of_operation_code")),
        phase_of_operation_title=as_text(raw.get("phase_of_operation_title")),
        type_of_financing=as_int(raw.get("type_of_financing")),
        type_of_financing_code=as_text(raw.get("type_of_financing_code")),
        type_of_financing_title=as_text(raw.get("type_of_financing_title")),
        type_of_installments=as_text(raw.get("type_of_installments")),
        type_of_installments_code=as_text(raw.get("type_of_installments_code")),
        payment_method=as_text(raw.get("payment_method")),
        payment_method_code=as_text(raw.get("payment_method_code")),
        payment_periodicity=as_text(raw.get("payment_periodicity")),
        payment_periodicity_code=as_text(raw.get("payment_periodicity_code")),
        purpose_of_the_credit=as_text(raw.get("purpose_of_the_credit")),
        purpose_of_the_credit_code=as_text(raw.get("purpose_of_the_credit_code")),
        contract_currency=as_text(raw.get("contract_currency")),
        contract_currency_code=as_text(raw.get("contract_currency_code")),
        installments_currency=as_text(raw.get("installments_currency")),
        installments_currency_code=as_text(raw.get("installments_currency_code")),
        start_date=as_text(raw.get("start_date")),
        expected_end_date=as_text(raw.get("expected_end_date")),
        real_end_date=as_text(raw.get("real_end_date")),
        accounting_date=as_text(raw.get("accounting_date")),
        contract_start_date_is_transaction_type=as_bool(
            raw.get("contract_start_date_is_transaction_type")
        ),
        repayments=tuple(_read_repayment(item) for item in as_dicts(raw.get("repayments"))),
        guarantees=tuple(as_dicts(raw.get("guarantees"))),
        related_persons=tuple(as_dicts(raw.get("related_persons"))),
    )


def _read_summary(raw: dict[str, Any]) -> ContractSummary:
    return ContractSummary(
        organization_id=as_int(raw.get("organization_id")),
        organization_name=as_text(raw.get("organization_name")),
        organization_name_code=as_text(raw.get("organization_name_code")),
        role_type=as_int(raw.get("role_type")),
        total_amount=as_int(raw.get("total_amount")),
        outstanding_amount=as_int(raw.get("outstanding_amount")),
        overdue_amount=as_int(raw.get("overdue_amount")),
        in_progress_contracts_count=as_int(raw.get("in_progress_contracts_count")),
        terminated_contracts_count=as_int(raw.get("terminated_contracts_count")),
        type_of_financing=as_text(raw.get("type_of_financing")),
        type_of_financing_code=as_text(raw.get("type_of_financing_code")),
        currency=as_text(raw.get("currency")),
        currency_code=as_text(raw.get("currency_code")),
    )


def _read_bounced_cheque(raw: dict[str, Any]) -> BouncedChequeSection | None:
    if not raw:
        return None
    return BouncedChequeSection(
        status=as_int(raw.get("status")),
        cheques=tuple(as_dicts(raw.get("bounced_cheques"))),
    )


def _read_judiciary(raw: dict[str, Any]) -> JudiciarySection | None:
    if not raw:
        return None
    inner = as_dict(raw.get("judiciary_data"))
    data = (
        JudiciaryData(
            national_code=as_text(inner.get("national_code")),
            accounting_date=as_text(inner.get("accounting_date")),
            bankruptcy_count=as_int(inner.get("bankruptcy_count")),
            insolvency_count=as_int(inner.get("insolvency_count")),
            insolvency_sum_penalty=as_int(inner.get("insolvency_sum_penalty")),
            sum_execute_count=as_int(inner.get("sum_execute_count")),
            sum_execute_sum_penalty_amount=as_int(inner.get("sum_execute_sum_penalty_amount")),
            sum_not_execute_count=as_int(inner.get("sum_not_execute_count")),
            sum_not_execute_sum_penalty_amount=as_int(
                inner.get("sum_not_execute_sum_penalty_amount")
            ),
            error_code=as_text(inner.get("error_code")),
            error_description=as_text(inner.get("error_description")),
        )
        if inner
        else None
    )
    return JudiciarySection(status=as_int(raw.get("status")), data=data)


def _read_pichak(raw: dict[str, Any]) -> PichakSection | None:
    if not raw:
        return None
    inner = as_dict(raw.get("person_cheques_data"))
    data = (
        PichakData(
            national_code=as_text(inner.get("national_code")),
            items=tuple(
                ChequeStatusCount(
                    check_status_id=as_int(item.get("check_status_id")),
                    check_status_title=as_text(item.get("check_status_title")),
                    count=as_int(item.get("count")),
                    total_amount=as_int(item.get("total_amount")),
                )
                for item in as_dicts(inner.get("person_cheque_items"))
            ),
            sum_count=as_int(inner.get("sum_count")),
            sum_total_amount=as_int(inner.get("sum_total_amount")),
        )
        if inner
        else None
    )
    return PichakSection(status=as_int(raw.get("status")), data=data)


def _read_tax_year(raw: dict[str, Any]) -> TaxYear:
    return TaxYear(
        year=as_int(raw.get("year")),
        national_code=as_text(raw.get("national_code")),
        accounting_date=as_text(raw.get("accounting_date")),
        daramad_ebrazi=as_int(raw.get("daramad_ebrazi")),
        maliat_ebrazi=as_int(raw.get("maliat_ebrazi")),
        maliat_tashkhisi=as_int(raw.get("maliat_tashkhisi")),
        maliat_ghati=as_int(raw.get("maliat_ghati")),
        maliat_vosoli=as_int(raw.get("maliat_vosoli")),
        bedehi_maliat_amalkard=as_int(raw.get("bedehi_maliat_amalkard")),
        bedehi_jarimeh_amalkard=as_int(raw.get("bedehi_jarimeh_amalkard")),
        jarayem=as_int(raw.get("jarayem")),
        maliate_hoghoghi_pardakhti_karfarma=as_int(raw.get("maliate_hoghoghi_pardakhti_karfarma")),
        maliate_hoghoghi_pardakhti_karmand=as_int(raw.get("maliate_hoghoghi_pardakhti_karmand")),
        dar_moed=as_bool(raw.get("dar_moed")),
        etelate_vosol_o_ejra=as_bool(raw.get("etelate_vosol_o_ejra")),
        is_maliat_pardakhti_type_and_date=as_bool(raw.get("is_maliat_pardakhti_type_and_date")),
        is_maliatghati_type_and_date=as_bool(raw.get("is_maliatghati_type_and_date")),
    )


def _read_tax(raw: dict[str, Any]) -> TaxSection | None:
    if not raw:
        return None
    return TaxSection(
        status=as_int(raw.get("status")),
        years=tuple(_read_tax_year(item) for item in as_dicts(raw.get("tax_result"))),
    )


def read_report(answer: Answer, reference_id: str) -> CreditReport:
    """Read a report, whether it is finished or still being assembled.

    A pending report has ``result`` absent entirely, so every section reads as empty and the record
    is falsy — which is the answer, not a failure.
    """
    data = answer.data
    result = as_dict(data.get("result"))
    return CreditReport(
        reference_id=as_text(data.get("reference_id")) or reference_id,
        status=as_text(data.get("status")),
        service=as_text(data.get("service")),
        completed_at=as_text(data.get("completed_at")),
        personal_information=_read_personal(as_dict(result.get("personal_information"))),
        score=_read_score(as_dict(result.get("score"))),
        direct_contracts=tuple(
            _read_contract(item) for item in as_dicts(result.get("direct_contracts"))
        ),
        indirect_contracts=tuple(
            _read_contract(item) for item in as_dicts(result.get("indirect_contracts"))
        ),
        summary_related_contracts=tuple(
            _read_summary(item) for item in as_dicts(result.get("summary_related_contracts"))
        ),
        inquiry_histories=tuple(
            InquiryHistory(bank_name=as_text(item.get("bank_name")), date=as_text(item.get("date")))
            for item in as_dicts(result.get("inquiry_histories"))
        ),
        inquiry_stats=tuple(
            InquiryStats(
                organization_type=as_text(item.get("organization_type")),
                organization_type_code=as_text(item.get("organization_type_code")),
                role_type=as_int(item.get("role_type")),
                last_month_inquiry_count=as_int(item.get("last_month_inquiry_count")),
                last_year_inquiry_count=as_int(item.get("last_year_inquiry_count")),
                contract_negative_status_count=as_int(item.get("contract_negative_status_count")),
                person_negative_status_count=as_int(item.get("person_negative_status_count")),
            )
            for item in as_dicts(result.get("inquiry_stats"))
        ),
        person_negative_status=tuple(
            NegativeStatus(
                date=as_text(item.get("date")),
                state=as_text(item.get("state")),
                state_code=as_text(item.get("state_code")),
                organization_name=as_text(item.get("organization_name")),
                organization_name_code=as_text(item.get("organization_name_code")),
                organization_type=as_text(item.get("organization_type")),
                organization_type_code=as_text(item.get("organization_type_code")),
            )
            for item in as_dicts(result.get("person_negative_status"))
        ),
        person_roles=tuple(
            PersonRole(
                code=as_text(item.get("code")),
                title=as_text(item.get("title")),
                number_of_contracts=as_int(item.get("number_of_contracts")),
            )
            for item in as_dicts(result.get("person_roles"))
        ),
        bounced_cheque=_read_bounced_cheque(as_dict(result.get("bounced_cheque"))),
        judiciary=_read_judiciary(as_dict(result.get("judiciary"))),
        pichak=_read_pichak(as_dict(result.get("pichak"))),
        tax=_read_tax(as_dict(result.get("tax"))),
        message=answer.message,
        raw=answer.raw,
    )
