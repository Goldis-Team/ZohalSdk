"""Utility services (خدماتی) — the records these seventeen endpoints return.

Dataclasses only. The widest family in the SDK: companies, addresses, vehicles, trust seals,
transliteration, ID-card OCR, a voice OTP, and seven kinds of bill.
"""

from dataclasses import dataclass, field
from typing import Any

from zohal_sdk.common.data import InquiryRecord


@dataclass(frozen=True)
class Company(InquiryRecord):
    """A registered company (استعلام اطلاعات شرکت)."""

    name: str | None = None
    national_id: str | None = None
    register_number: str | None = None
    company_type: str | None = None
    """e.g. ``"شرکت سهامی خاص"``."""

    address: str | None = None
    postal_code: str | None = None
    phone_number: str | None = None
    fax_number: str | None = None
    email_address: str | None = None
    register_date: str | None = None
    issuance_date: str | None = None
    created_at: str | None = None
    activity_end_date: str | None = None
    """When the company's registered activity ends. Empty for a going concern, so ``None``."""


@dataclass(frozen=True)
class BoardMember:
    """One seat on a company's board."""

    name: str | None = None
    position: str | None = None
    """e.g. ``"مدیر عامل"``, ``"بازرس اصلی"``."""

    duration: str | None = None
    """The term as the registry words it — ``"2 سال"``, or ``"G:تا پایان سال مالی"``."""

    start_date: str | None = None
    end_date: str | None = None
    """Set only on the history inquiry; the current-board inquiry sends no end date."""


@dataclass(frozen=True)
class BoardMembers(InquiryRecord):
    """A company's board, current or historical (استعلام اعضای هیئت‌مدیره شرکت).

    The same record for both inquiries; only the history one fills in
    :attr:`BoardMember.end_date`.
    """

    company_title: str | None = None
    members: tuple[BoardMember, ...] = ()


@dataclass(frozen=True)
class PostalAddress(InquiryRecord):
    """The address behind a postal code (استعلام کد پستی).

    Zohal nests these under an ``address`` object; they are lifted to the top here, since a record
    whose only field is another record helps nobody.
    """

    province: str | None = None
    town: str | None = None
    district: str | None = None
    street: str | None = None
    street2: str | None = None
    """The larger street the address is off, where the registry records one."""

    number: int | None = None
    """The building number."""

    building_name: str | None = None
    floor: str | None = None
    """A string, not a number — basements come back as ``"-1"``."""

    side_floor: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class VehicleViolationsSummary(InquiryRecord):
    """What a vehicle owes in total (استعلام خلافی خودرو).

    Amounts are in **Rial** and arrive as decimal strings; they are read as integers here.
    """

    plate: str | None = None
    """The plate as the police system formats it, in Persian digits."""

    inquire_price: int | None = None
    """Total outstanding, in Rial."""

    warning_price: int | None = None
    """The portion still within the discounted window, in Rial."""

    payment_id: str | None = None
    paper_id: str | None = None
    ejr_inquire_no: str | None = None
    """The enforcement reference for this inquiry."""

    price_status: str | None = None
    page_count: int | None = None


@dataclass(frozen=True)
class VehicleViolation:
    """A single traffic violation."""

    warning_id: str | None = None
    serial_no: str | None = None
    paper_id: str | None = None
    payment_id: str | None = None

    final_price: int | None = None
    """The fine, in Rial."""

    violation_type: str | None = None
    """What the fine is for. Lifted out of Zohal's nested ``violation_type`` object."""

    violation_type_id: str | None = None
    delivery_type: str | None = None
    """How the notice was served — lifted out of the nested ``violation_delivery_type`` object."""

    occurred_at: str | None = None
    """Jalali date and time, e.g. ``"1399/01/25 - 13:06"``."""

    occurred_time: int | None = None
    """Zohal's ``violation_occure_time``, an integer whose unit it does not document."""

    address: str | None = None
    """Where it happened. Zohal spells this field ``violatoin_address``; the typo is theirs."""

    has_image: bool | None = None
    investigation_ability: bool | None = None
    """Whether the fine can still be contested."""


@dataclass(frozen=True)
class VehicleViolations(InquiryRecord):
    """Every outstanding violation, itemised (استعلام خلافی خودرو با جزئیات)."""

    violations: tuple[VehicleViolation, ...] = ()

    @property
    def total(self) -> int:
        """The sum of every fine, in Rial — the itemised inquiry reports no total of its own."""
        return sum(item.final_price or 0 for item in self.violations)


@dataclass(frozen=True)
class Enamad(InquiryRecord):
    """A site's Enamad trust seal (استعلام Enamad)."""

    domain: str | None = None
    name: str | None = None
    """The seal holder's registered name."""

    nameper: str | None = None
    """Their trading name, where it differs — Zohal's own field name."""

    id: int | None = None
    logo_level: int | None = None
    """The star rating on the seal, 1–4."""

    expired: bool | None = None
    approve_date: str | None = None
    expiry_date: str | None = None
    city_name: str | None = None
    state_name: str | None = None
    srv_text: str | None = None
    """The services the seal covers, comma-separated in Persian."""

    status_message: str | None = None
    """Enamad's own verdict, e.g. ``"نماد دارد."``. Kept apart from
    :attr:`~zohal_sdk.common.data.InquiryRecord.message`, which is Zohal's."""

    def __bool__(self) -> bool:
        """Truthy for a seal that exists and has not expired."""
        return self.id is not None and not self.expired


@dataclass(frozen=True)
class Finglish(InquiryRecord):
    """A Persian name transliterated (تبدیل نام فارسی به فینگلیش)."""

    finglish_text: str | None = None


@dataclass(frozen=True)
class NationalCardFront:
    """What OCR read off the front of a national card. Nested inside :class:`NationalCardOcr`."""

    result: bool | None = None
    """Whether the OCR believes it read the card successfully."""

    national_code: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    father_name: str | None = None
    birth_date: str | None = None
    expiration_date: str | None = None
    city: str | None = None
    province: str | None = None

    face_photo: str | None = None
    """The holder's photograph, base64. Large — do not log this record whole."""


@dataclass(frozen=True)
class NationalCardOcr(InquiryRecord):
    """A national card read by OCR (OCR کارت ملی)."""

    front: NationalCardFront | None = None

    back: dict[str, Any] = field(default_factory=dict[str, Any])
    """The back of the card, untouched.

    Zohal's published response has this as ``null`` and documents no fields for it, so there is
    nothing here to model honestly — inventing a shape would be worse than passing through what
    actually arrives. If your account returns a populated back, read it from this dict and open an
    issue with what you see.
    """


@dataclass(frozen=True)
class VoiceOtp(InquiryRecord):
    """The acknowledgement for a voice OTP call (OTP صوتی).

    Zohal documents the request and publishes no response body at all, so this record carries
    Zohal's message and the raw payload and claims nothing further. ``data`` is whatever it sent.
    """

    data: dict[str, Any] = field(default_factory=dict[str, Any])


@dataclass(frozen=True)
class BillTerm:
    """One term of a telecom bill — the mid-cycle or the final one."""

    amount: int | None = None
    """In Rial."""

    bill_id: str | None = None
    """شناسه قبض."""

    payment_id: str | None = None
    """شناسه پرداخت."""


@dataclass(frozen=True)
class MobileBill(InquiryRecord):
    """A telecom bill (همراه اول، ایرانسل، رایتل، تلفن ثابت).

    Both operators bill in two terms: ``mid_term`` is the running total for the current cycle and
    ``final_term`` is the last closed one. Either can be absent.
    """

    mid_term: BillTerm | None = None
    final_term: BillTerm | None = None


@dataclass(frozen=True)
class UtilityBill(InquiryRecord):
    """A water or electricity bill (قبض آب، قبض برق)."""

    bill_id: str | None = None
    payment_id: str | None = None
    amount: int | None = None
    """In Rial. Zero means nothing is outstanding."""

    full_name: str | None = None
    """The account holder."""

    address: str | None = None
    account_type: str | None = None
    """e.g. ``"مسکونی"``, ``"خانگی"``."""

    payment_date: str | None = None
    current_date: str | None = None
    previous_date: str | None = None


@dataclass(frozen=True)
class GasBill(InquiryRecord):
    """A gas bill (قبض گاز).

    Close to :class:`UtilityBill`, but the gas utility names its meter-reading dates differently
    and reports a consumption class instead of an account type — so it is its own record rather
    than a shared one with fields that mean different things per utility.
    """

    bill_id: str | None = None
    payment_id: str | None = None
    amount: int | None = None
    full_name: str | None = None
    address: str | None = None
    consumption_type: str | None = None
    """e.g. ``"خانگي بدون چیلر"``."""

    payment_date: str | None = None
    current_reading_date: str | None = None
    previous_reading_date: str | None = None
