"""Credit scoring (استعلام اعتبارسنجی) — the records this flow returns.

Dataclasses only, and by some distance the deepest payload in the API: a full report is assembled
from the credit bureau, the Central Bank's cheque registries, the judiciary and the tax authority,
each contributing its own section with its own status.

Every section is modelled rather than left as ``dict[str, Any]``. A credit decision read through
raw dictionary lookups is precisely where the typing this SDK exists for would have earned its
keep and didn't — and it is where a silent key rename upstream turns into a ``KeyError`` in front
of a customer rather than a ``None`` you can see.

Two things are deliberately *not* modelled, because Zohal publishes no fields for them: the
contents of :attr:`BouncedChequeSection.cheques`, and a contract's ``guarantees`` and
``related_persons``, all of which are empty or ``null`` in every published example. Those arrive as
raw dicts, documented as such.
"""

from dataclasses import dataclass, field
from typing import Any

from zohal_sdk.common.data import InquiryRecord
from zohal_sdk.services.credit.constants import SECTION_OK, STATUS_COMPLETED, TERMINAL_STATUSES


@dataclass(frozen=True)
class CreditOtpRequest(InquiryRecord):
    """The acknowledgement for a credit OTP (ارسال OTP).

    This flow answers outside Zohal's usual envelope — the body is just these two fields — so
    :attr:`~zohal_sdk.common.data.InquiryRecord.message` is ``None`` here.
    """

    reference_id: str | None = None
    """Carry this through the whole flow: it identifies the OTP, and later the report."""

    status: str | None = None
    """``"pending"`` once the code has been sent."""


@dataclass(frozen=True)
class CreditOtpVerification(InquiryRecord):
    """The answer to submitting a credit OTP (اعتبارسنجی OTP).

    Zohal publishes no response body for this step, so the record carries whatever arrived and
    claims no more. A successful call is one that did not raise; the report is then collected
    against the same ``reference_id``.
    """

    reference_id: str | None = None
    status: str | None = None
    data: dict[str, Any] = field(default_factory=dict[str, Any])
    """The whole body, untouched, since its shape is unpublished."""


@dataclass(frozen=True)
class PersonalInformation:
    """Who the report is about, as the credit bureau holds them."""

    national_code: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    father_name: str | None = None
    birth_date: str | None = None
    gender: str | None = None
    """Persian, e.g. ``"مرد"``."""

    marital_status: str | None = None
    has_blocked_contract: bool | None = None
    """Whether any credit contract against this person is currently blocked."""


@dataclass(frozen=True)
class ScoreCode:
    """One reason behind the score — the bureau's explanation of what moved it."""

    code: str | None = None
    """e.g. ``"NGS1"``, ``"AGE1"``."""

    description: str | None = None
    """What that code means, in Persian."""


@dataclass(frozen=True)
class CreditScore:
    """The score itself, and why it is what it is."""

    score: int | None = None
    """The numeric score. Higher is better."""

    risk: str | None = None
    """The risk band, e.g. ``"C2"``."""

    description: str | None = None
    """The band in words, e.g. ``"ریسک متوسط"``."""

    score_type: str | None = None
    """How the score was arrived at, in Zohal's own words."""

    inquiry_created_date: str | None = None
    previous_score: bool | None = None
    """Whether a previous score exists for this person."""

    previous_score_date: str | None = None
    codes: tuple[ScoreCode, ...] = ()
    """The factors behind the score, strongest first as the bureau ordered them."""


@dataclass(frozen=True)
class Repayment:
    """One month of a contract's repayment history."""

    date: str | None = None
    """Jalali year and month, e.g. ``"1403/7"``."""

    negative_contract_status: int | None = None
    """``0`` for a month paid as agreed; higher values grade how far behind it fell."""

    overdue_amount: int | None = None
    total_number_of_overdue: int | None = None


@dataclass(frozen=True)
class CreditContract:
    """One credit facility — a loan, a card, a guarantee.

    ``direct_contracts`` are facilities in this person's own name; ``indirect_contracts`` are ones
    they are exposed to through somebody else's, as guarantor or co-signatory.

    Amounts are in the contract's own ``contract_currency``, which is Rial on essentially every
    domestic facility. Most fields arrive paired with a ``*_code``: the human-readable Persian text
    and the bureau's code for the same thing, and both are kept — the text is what a person reads,
    the code is what survives a rewording upstream.
    """

    contract_id: int | None = None
    contract_number: str | None = None

    organization_name: str | None = None
    """The lender, e.g. ``"بانک پاسارگاد"``."""

    organization_name_code: str | None = None
    organization_type: str | None = None
    organization_type_code: str | None = None

    customer_role: int | None = None
    customer_role_code: str | None = None
    customer_role_title: str | None = None
    """This person's role on the contract, e.g. ``"متقاضی اصلی"``."""

    total_amount: int | None = None
    """The facility's principal."""

    instalment_amount: int | None = None
    """Zohal's spelling. The amount due each period."""

    outstanding_amount: int | None = None
    """Still owed and not yet due."""

    overdue_amount: int | None = None
    """Owed and past due — the number that matters most in this record."""

    total_number_of_installments: int | None = None
    total_number_of_outstanding: int | None = None
    total_number_of_overdue: int | None = None

    negative_contract_status: str | None = None
    """e.g. ``"فاقد وضعیت منفی"`` — no adverse status."""

    negative_contract_status_code: str | None = None

    phase_of_operation: int | None = None
    phase_of_operation_code: str | None = None
    phase_of_operation_title: str | None = None
    """Where the contract stands, e.g. ``"خاتمه یافته به درخواست مشتری"``."""

    type_of_financing: int | None = None
    type_of_financing_code: str | None = None
    type_of_financing_title: str | None = None
    type_of_installments: str | None = None
    type_of_installments_code: str | None = None

    payment_method: str | None = None
    payment_method_code: str | None = None
    payment_periodicity: str | None = None
    payment_periodicity_code: str | None = None
    purpose_of_the_credit: str | None = None
    purpose_of_the_credit_code: str | None = None

    contract_currency: str | None = None
    contract_currency_code: str | None = None
    installments_currency: str | None = None
    installments_currency_code: str | None = None

    start_date: str | None = None
    expected_end_date: str | None = None
    real_end_date: str | None = None
    accounting_date: str | None = None
    contract_start_date_is_transaction_type: bool | None = None

    repayments: tuple[Repayment, ...] = ()
    """Month by month, oldest first as the bureau sent it."""

    guarantees: tuple[dict[str, Any], ...] = ()
    """Security pledged against the facility. Empty in every published example and undocumented,
    so passed through untouched rather than given an invented shape."""

    related_persons: tuple[dict[str, Any], ...] = ()
    """Guarantors and co-signatories. Undocumented for the same reason."""


@dataclass(frozen=True)
class ContractSummary:
    """One lender's total exposure to this person, across all their contracts with it."""

    organization_id: int | None = None
    organization_name: str | None = None
    organization_name_code: str | None = None
    role_type: int | None = None

    total_amount: int | None = None
    outstanding_amount: int | None = None
    overdue_amount: int | None = None

    in_progress_contracts_count: int | None = None
    terminated_contracts_count: int | None = None

    type_of_financing: str | None = None
    type_of_financing_code: str | None = None
    currency: str | None = None
    currency_code: str | None = None


@dataclass(frozen=True)
class InquiryHistory:
    """A time somebody else pulled this person's credit file."""

    bank_name: str | None = None
    date: str | None = None


@dataclass(frozen=True)
class InquiryStats:
    """How often this person's file has been pulled, by one type of institution."""

    organization_type: str | None = None
    organization_type_code: str | None = None
    role_type: int | None = None
    last_month_inquiry_count: int | None = None
    last_year_inquiry_count: int | None = None
    contract_negative_status_count: int | None = None
    person_negative_status_count: int | None = None


@dataclass(frozen=True)
class NegativeStatus:
    """An adverse mark recorded against the person by an institution."""

    date: str | None = None
    state: str | None = None
    """What the mark is, in Persian."""

    state_code: str | None = None
    organization_name: str | None = None
    organization_name_code: str | None = None
    organization_type: str | None = None
    organization_type_code: str | None = None


@dataclass(frozen=True)
class PersonRole:
    """A role this person holds across their contracts, and how many carry it."""

    code: str | None = None
    title: str | None = None
    number_of_contracts: int | None = None


@dataclass(frozen=True)
class ReportSection:
    """Base for the sections that come from a separate government system.

    Each carries its own ``status``, because each is a separate upstream that can answer or not
    independently of the others. ``404`` means that system had nothing on this person — for the
    bounced-cheque registry that is the *good* answer — so a section being absent is information,
    not a failure, and never raises.
    """

    status: int | None = None

    @property
    def answered(self) -> bool:
        """Whether this upstream returned data. ``False`` covers both "nothing on file" and
        "that system was unreachable" — :attr:`status` distinguishes them."""
        return self.status == SECTION_OK


@dataclass(frozen=True)
class BouncedChequeSection(ReportSection):
    """The Central Bank's returned-cheque registry.

    ``status=404`` with no cheques is the answer for a person who has none, and is the outcome you
    are hoping for rather than an error.
    """

    cheques: tuple[dict[str, Any], ...] = ()
    """Undocumented — ``null`` in every published example — so passed through untouched."""


@dataclass(frozen=True)
class JudiciaryData:
    """What the judiciary holds: bankruptcies, insolvencies and enforcement orders."""

    national_code: str | None = None
    accounting_date: str | None = None
    bankruptcy_count: int | None = None
    insolvency_count: int | None = None
    insolvency_sum_penalty: int | None = None
    sum_execute_count: int | None = None
    """Enforcement orders already executed."""

    sum_execute_sum_penalty_amount: int | None = None
    sum_not_execute_count: int | None = None
    """Enforcement orders outstanding."""

    sum_not_execute_sum_penalty_amount: int | None = None
    error_code: str | None = None
    error_description: str | None = None


@dataclass(frozen=True)
class JudiciarySection(ReportSection):
    """The judiciary's section of the report."""

    data: JudiciaryData | None = None


@dataclass(frozen=True)
class ChequeStatusCount:
    """How many of this person's cheques sit in one state, and for how much."""

    check_status_id: int | None = None
    check_status_title: str | None = None
    """e.g. ``"نقدشده"`` cleared, ``"برگشتی"`` returned, ``"سررسیدآتی"`` not yet due."""

    count: int | None = None
    total_amount: int | None = None


@dataclass(frozen=True)
class PichakData:
    """The Pichak cheque registry's view of this person."""

    national_code: str | None = None
    items: tuple[ChequeStatusCount, ...] = ()
    sum_count: int | None = None
    sum_total_amount: int | None = None


@dataclass(frozen=True)
class PichakSection(ReportSection):
    """The Pichak section of the report."""

    data: PichakData | None = None


@dataclass(frozen=True)
class TaxYear:
    """One tax year, as the tax authority reports it.

    Field names are kept exactly as Zohal sends them — Finglish transliterations of the Persian
    terms — rather than translated. A translation would be a guess at which English accounting
    term each maps to, and would break the one thing that makes this section auditable: being able
    to line a field up against the raw payload and the tax authority's own wording.
    """

    year: int | None = None
    national_code: str | None = None
    accounting_date: str | None = None

    daramad_ebrazi: int | None = None
    """درآمد ابرازی — declared income."""

    maliat_ebrazi: int | None = None
    """مالیات ابرازی — declared tax."""

    maliat_tashkhisi: int | None = None
    """مالیات تشخیصی — assessed tax."""

    maliat_ghati: int | None = None
    """مالیات قطعی — final tax."""

    maliat_vosoli: int | None = None
    """مالیات وصولی — tax collected."""

    bedehi_maliat_amalkard: int | None = None
    """بدهی مالیات عملکرد — outstanding performance tax."""

    bedehi_jarimeh_amalkard: int | None = None
    """بدهی جریمه عملکرد — outstanding performance penalty."""

    jarayem: int | None = None
    """جرایم — penalties."""

    maliate_hoghoghi_pardakhti_karfarma: int | None = None
    """Payroll tax paid by the employer."""

    maliate_hoghoghi_pardakhti_karmand: int | None = None
    """Payroll tax paid by the employee."""

    dar_moed: bool | None = None
    """در موعد — whether the filing was on time."""

    etelate_vosol_o_ejra: bool | None = None
    """Whether collection or enforcement information exists for this year."""

    is_maliat_pardakhti_type_and_date: bool | None = None
    is_maliatghati_type_and_date: bool | None = None


@dataclass(frozen=True)
class TaxSection(ReportSection):
    """The tax authority's section of the report."""

    years: tuple[TaxYear, ...] = ()


@dataclass(frozen=True)
class CreditReport(InquiryRecord):
    """A completed credit report (دریافت نتیجه).

    Falsy until :attr:`status` is ``"completed"``, so a report still being assembled never reads as
    a finished one. While pending, every section below is empty and
    :attr:`~CreditReport.personal_information` is ``None`` — poll, or wait for the callback.
    """

    reference_id: str | None = None
    status: str | None = None
    """``"pending"`` while Zohal assembles it, ``"completed"`` when it is done."""

    service: str | None = None
    """Which Zohal service produced it, e.g. ``"استعلام اعتبارسنجی"``."""

    completed_at: str | None = None
    """ISO 8601, in Zohal's local time."""

    personal_information: PersonalInformation | None = None
    score: CreditScore | None = None

    direct_contracts: tuple[CreditContract, ...] = ()
    """Facilities in this person's own name."""

    indirect_contracts: tuple[CreditContract, ...] = ()
    """Facilities they are exposed to through someone else's — as guarantor, typically."""

    summary_related_contracts: tuple[ContractSummary, ...] = ()
    """One row per lender, totalling that lender's exposure."""

    inquiry_histories: tuple[InquiryHistory, ...] = ()
    inquiry_stats: tuple[InquiryStats, ...] = ()
    person_negative_status: tuple[NegativeStatus, ...] = ()
    person_roles: tuple[PersonRole, ...] = ()

    bounced_cheque: BouncedChequeSection | None = None
    judiciary: JudiciarySection | None = None
    pichak: PichakSection | None = None
    tax: TaxSection | None = None

    @property
    def is_final(self) -> bool:
        """Whether this status will not change again — what the polling helpers wait on."""
        return self.status is not None and self.status.lower() in TERMINAL_STATUSES

    @property
    def is_completed(self) -> bool:
        return (self.status or "").lower() == STATUS_COMPLETED

    @property
    def total_overdue(self) -> int:
        """The sum of every overdue amount across direct contracts.

        Direct contracts only: an indirect one is somebody else's debt that this person guaranteed,
        and adding the two together would overstate what they actually owe.
        """
        return sum(contract.overdue_amount or 0 for contract in self.direct_contracts)

    def __bool__(self) -> bool:
        return self.is_completed
