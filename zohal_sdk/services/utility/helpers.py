"""Utility services (خدماتی) — payload building and response reading.

Pure functions, called by both engines.
"""

from typing import Any

from zohal_sdk.common.engine import Answer
from zohal_sdk.common.utils import (
    as_bool,
    as_dict,
    as_dicts,
    as_int,
    as_text,
    check_bill_id,
    check_digits,
    check_mobile,
    check_national_code,
    check_national_id,
    check_phone,
    check_postal_code,
    check_required,
)
from zohal_sdk.services.utility.data import (
    BillTerm,
    BoardMember,
    BoardMembers,
    Company,
    Enamad,
    Finglish,
    GasBill,
    MobileBill,
    NationalCardFront,
    NationalCardOcr,
    PostalAddress,
    UtilityBill,
    VehicleViolation,
    VehicleViolations,
    VehicleViolationsSummary,
    VoiceOtp,
)


def company_payload(national_id: str) -> dict[str, Any]:
    return {"national_id": check_national_id(national_id)}


def postal_code_payload(postal_code: str) -> dict[str, Any]:
    return {"postal_code": check_postal_code(postal_code)}


def vehicle_payload(
    plate_number: str, region_code: str, national_code: str, mobile: str
) -> dict[str, Any]:
    return {
        # A plate is written with a Persian letter in the middle — "11 ب 111" — so the spacing and
        # the letter are meaningful and only the digits are folded.
        "plate_number": check_required(plate_number, field="plate_number", label="plate number"),
        "region_code": check_digits(
            region_code, length=2, field="region_code", label="region code"
        ),
        # The police system sends the result to this number as well as returning it, which is why
        # both the owner's national code and a mobile are required.
        "national_code": check_national_code(national_code),
        "mobile": check_mobile(mobile),
    }


def enamad_payload(website: str) -> dict[str, Any]:
    return {"website": check_required(website, field="website", label="website")}


def finglish_payload(persian_text: str) -> dict[str, Any]:
    return {
        "persian_text": check_required(persian_text, field="persian_text", label="Persian text")
    }


def voice_otp_payload(mobile: str, code: str) -> dict[str, Any]:
    return {
        "mobile": check_mobile(mobile),
        "code": check_required(code, field="code", label="OTP code"),
    }


def mobile_bill_payload(mobile: str) -> dict[str, Any]:
    return {"mobile": check_mobile(mobile)}


def fixed_line_bill_payload(phone_number: str) -> dict[str, Any]:
    """Zohal names this field ``mobile`` even on the fixed-line endpoint. Sent under its name."""
    return {"mobile": check_phone(phone_number)}


def bill_payload(bill_id: str) -> dict[str, Any]:
    return {"bill_id": check_bill_id(bill_id)}


def read_company(answer: Answer) -> Company:
    data = answer.data
    return Company(
        name=as_text(data.get("name")),
        national_id=as_text(data.get("national_id")),
        register_number=as_text(data.get("register_number")),
        company_type=as_text(data.get("company_type")),
        address=as_text(data.get("address")),
        postal_code=as_text(data.get("postal_code")),
        phone_number=as_text(data.get("phone_number")),
        fax_number=as_text(data.get("fax_number")),
        email_address=as_text(data.get("email_address")),
        register_date=as_text(data.get("register_date")),
        issuance_date=as_text(data.get("issuance_date")),
        created_at=as_text(data.get("created_at")),
        activity_end_date=as_text(data.get("activity_end_date")),
        message=answer.message,
        raw=answer.raw,
    )


def _read_board_member(raw: dict[str, Any]) -> BoardMember:
    return BoardMember(
        name=as_text(raw.get("name")),
        position=as_text(raw.get("position")),
        duration=as_text(raw.get("duration")),
        start_date=as_text(raw.get("start_date")),
        end_date=as_text(raw.get("end_date")),
    )


def read_board_members(answer: Answer) -> BoardMembers:
    return BoardMembers(
        company_title=as_text(answer.data.get("company_title")),
        members=tuple(
            _read_board_member(item) for item in as_dicts(answer.data.get("board_members"))
        ),
        message=answer.message,
        raw=answer.raw,
    )


def read_postal_address(answer: Answer) -> PostalAddress:
    address = as_dict(answer.data.get("address"))
    return PostalAddress(
        province=as_text(address.get("province")),
        town=as_text(address.get("town")),
        district=as_text(address.get("district")),
        street=as_text(address.get("street")),
        street2=as_text(address.get("street2")),
        number=as_int(address.get("number")),
        building_name=as_text(address.get("building_name")),
        floor=as_text(address.get("floor")),
        side_floor=as_text(address.get("side_floor")),
        description=as_text(address.get("description")),
        message=answer.message,
        raw=answer.raw,
    )


def read_vehicle_summary(answer: Answer) -> VehicleViolationsSummary:
    data = answer.data
    return VehicleViolationsSummary(
        plate=as_text(data.get("plate")),
        # These arrive as decimal strings — "10000000" — not as numbers.
        inquire_price=as_int(data.get("inquire_price")),
        warning_price=as_int(data.get("warning_price")),
        payment_id=as_text(data.get("payment_id")),
        paper_id=as_text(data.get("paper_id")),
        ejr_inquire_no=as_text(data.get("ejr_inquire_no")),
        price_status=as_text(data.get("price_status")),
        page_count=as_int(data.get("page_count")),
        message=answer.message,
        raw=answer.raw,
    )


def _read_violation(raw: dict[str, Any]) -> VehicleViolation:
    # Zohal nests each of these in a one-key object named after itself; they are lifted here so a
    # caller reads `violation.violation_type` rather than digging two levels for a string.
    kind = as_dict(raw.get("violation_type"))
    delivery = as_dict(raw.get("violation_delivery_type"))
    return VehicleViolation(
        warning_id=as_text(raw.get("warning_id")),
        serial_no=as_text(raw.get("serial_no")),
        paper_id=as_text(raw.get("paper_id")),
        payment_id=as_text(raw.get("payment_id")),
        final_price=as_int(raw.get("final_price")),
        violation_type=as_text(kind.get("violation_type")),
        violation_type_id=as_text(kind.get("violation_type_id")),
        delivery_type=as_text(delivery.get("violation_delivery_type")),
        occurred_at=as_text(raw.get("violation_occure_date")),
        occurred_time=as_int(raw.get("violation_occure_time")),
        # Zohal's own spelling of this key is `violatoin_address`.
        address=as_text(raw.get("violatoin_address")) or as_text(raw.get("violation_address")),
        has_image=as_bool(raw.get("has_image")),
        investigation_ability=as_bool(raw.get("investigation_ability")),
    )


def read_vehicle_violations(answer: Answer) -> VehicleViolations:
    return VehicleViolations(
        violations=tuple(_read_violation(item) for item in as_dicts(answer.data.get("warnings"))),
        message=answer.message,
        raw=answer.raw,
    )


def read_enamad(answer: Answer) -> Enamad:
    data = answer.data
    return Enamad(
        domain=as_text(data.get("domain")),
        name=as_text(data.get("name")),
        nameper=as_text(data.get("nameper")),
        id=as_int(data.get("id")),
        logo_level=as_int(data.get("logolevel")),
        expired=as_bool(data.get("expired")),
        approve_date=as_text(data.get("approve_date")),
        expiry_date=as_text(data.get("expiry_date")),
        city_name=as_text(data.get("city_name")),
        state_name=as_text(data.get("state_name")),
        srv_text=as_text(data.get("srv_text")),
        # Enamad's verdict lives in `data.message`, one level below Zohal's own `message`.
        status_message=as_text(data.get("message")),
        message=answer.message,
        raw=answer.raw,
    )


def read_finglish(answer: Answer) -> Finglish:
    return Finglish(
        finglish_text=as_text(answer.data.get("finglish_text")),
        message=answer.message,
        raw=answer.raw,
    )


def _read_card_front(raw: dict[str, Any]) -> NationalCardFront | None:
    if not raw:
        return None
    return NationalCardFront(
        result=as_bool(raw.get("result")),
        national_code=as_text(raw.get("national_code")),
        first_name=as_text(raw.get("first_name")),
        last_name=as_text(raw.get("last_name")),
        father_name=as_text(raw.get("father_name")),
        birth_date=as_text(raw.get("birth_date")),
        expiration_date=as_text(raw.get("expiration_date")),
        city=as_text(raw.get("city")),
        province=as_text(raw.get("province")),
        face_photo=as_text(raw.get("face_photo")),
    )


def read_national_card_ocr(answer: Answer) -> NationalCardOcr:
    return NationalCardOcr(
        front=_read_card_front(as_dict(answer.data.get("front"))),
        back=as_dict(answer.data.get("back")),
        message=answer.message,
        raw=answer.raw,
    )


def read_voice_otp(answer: Answer) -> VoiceOtp:
    return VoiceOtp(data=answer.data, message=answer.message, raw=answer.raw)


def _read_term(raw: dict[str, Any]) -> BillTerm | None:
    if not raw:
        return None
    return BillTerm(
        amount=as_int(raw.get("amount")),
        bill_id=as_text(raw.get("bill_id")),
        payment_id=as_text(raw.get("payment_id")),
    )


def read_mobile_bill(answer: Answer) -> MobileBill:
    return MobileBill(
        mid_term=_read_term(as_dict(answer.data.get("mid_term"))),
        final_term=_read_term(as_dict(answer.data.get("final_term"))),
        message=answer.message,
        raw=answer.raw,
    )


def read_utility_bill(answer: Answer) -> UtilityBill:
    data = answer.data
    return UtilityBill(
        bill_id=as_text(data.get("bill_id")),
        payment_id=as_text(data.get("payment_id")),
        amount=as_int(data.get("amount")),
        full_name=as_text(data.get("full_name")),
        address=as_text(data.get("address")),
        account_type=as_text(data.get("account_type")),
        payment_date=as_text(data.get("payment_date")),
        current_date=as_text(data.get("current_date")),
        previous_date=as_text(data.get("previous_date")),
        message=answer.message,
        raw=answer.raw,
    )


def read_gas_bill(answer: Answer) -> GasBill:
    data = answer.data
    return GasBill(
        bill_id=as_text(data.get("bill_id")),
        payment_id=as_text(data.get("payment_id")),
        amount=as_int(data.get("amount")),
        full_name=as_text(data.get("full_name")),
        address=as_text(data.get("address")),
        consumption_type=as_text(data.get("consumption_type")),
        payment_date=as_text(data.get("payment_date")),
        current_reading_date=as_text(data.get("current_reading_date")),
        previous_reading_date=as_text(data.get("previous_reading_date")),
        message=answer.message,
        raw=answer.raw,
    )
