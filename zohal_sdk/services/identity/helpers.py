"""Identity (احراز هویت) — payload building and response reading.

Pure functions, called by both engines.
"""

from typing import Any

from zohal_sdk.common.data import MatchResult
from zohal_sdk.common.engine import Answer
from zohal_sdk.common.utils import (
    as_bool,
    as_text,
    check_birth_date,
    check_card_number,
    check_iban,
    check_mobile,
    check_national_code,
)
from zohal_sdk.services.identity.data import NationalIdentity


def shahkar_payload(national_code: str, mobile: str) -> dict[str, Any]:
    return {
        "national_code": check_national_code(national_code),
        "mobile": check_mobile(mobile),
    }


def national_identity_payload(national_code: str, birth_date: str) -> dict[str, Any]:
    return {
        "national_code": check_national_code(national_code),
        "birth_date": check_birth_date(birth_date),
    }


def iban_with_national_code_payload(
    iban: str, national_code: str, birth_date: str
) -> dict[str, Any]:
    # Note the key: `IBAN` here, but `iban` on the banking family's own IBAN inquiry.
    return {
        "IBAN": check_iban(iban),
        "national_code": check_national_code(national_code),
        "birth_date": check_birth_date(birth_date),
    }


def card_with_national_code_payload(
    card_number: str, national_code: str, birth_date: str
) -> dict[str, Any]:
    return {
        "card_number": check_card_number(card_number),
        "national_code": check_national_code(national_code),
        "birth_date": check_birth_date(birth_date),
    }


def read_match(answer: Answer) -> MatchResult:
    """A missing ``matched`` reads as ``False`` — an absent verdict must never pass for a match."""
    return MatchResult(
        matched=bool(as_bool(answer.data.get("matched"))),
        message=answer.message,
        raw=answer.raw,
    )


def read_national_identity(answer: Answer) -> NationalIdentity:
    data = answer.data
    return NationalIdentity(
        matched=bool(as_bool(data.get("matched"))),
        national_code=as_text(data.get("national_code")),
        first_name=as_text(data.get("first_name")),
        last_name=as_text(data.get("last_name")),
        father_name=as_text(data.get("father_name")),
        alive=as_bool(data.get("alive")),
        is_dead=as_bool(data.get("is_dead")),
        message=answer.message,
        raw=answer.raw,
    )
