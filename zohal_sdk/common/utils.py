"""The normalisation, checks and coercions every family needs, written once so they cannot drift.

Two halves, pulling in opposite directions on purpose.

**Going out**, the checks are strict and raise. Every Zohal endpoint is billed per call, and an
input whose own checksum does not hold cannot become a real answer no matter what Zohal does with
it — so it is refused here, for free, instead of being paid for and answered with ``result=6``.
Normalisation runs first: a national code arriving from a web form as ``«۰۰۲۱۲۳۴۵۶۷»`` is folded to
ASCII digits rather than rejected, because Persian digits are what Iranian users actually type.

**Coming back**, the coercions are forgiving and return ``None``. Records are descriptive, nothing
settles on them, and a field that arrives as ``""`` is better reported as absent than as a crash in
the middle of parsing an answer that has already been paid for.
"""

import re
from typing import Any, cast

from zohal_sdk.common.exceptions import ZohalValidationError

#: Persian ۰-۹ and Arabic-Indic ٠-٩ folded onto ASCII. Iranian keyboards produce both, often mixed
#: in one field, and every Zohal endpoint wants ASCII.
_DIGIT_MAP = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

#: Stripped from identifiers before validation: the separators people paste in from bank
#: statements, spreadsheets and SMS messages.
_SEPARATORS = re.compile(r"[\s\-_.]+")

#: Digits in the order mod-97 wants them, once an IBAN has been rotated.
_IBAN_LETTERS = {"I": "18", "R": "27"}


def fold_digits(text: str) -> str:
    """Persian and Arabic-Indic digits folded to ASCII. Everything else passes through."""
    return text.translate(_DIGIT_MAP)


def normalize(value: Any) -> str:
    """Fold digits and strip the separators, leaving something worth validating.

    Applied to every identifier before it is checked, so ``"6362-1411-1234-5678"``,
    ``"۶۳۶۲۱۴۱۱۱۲۳۴۵۶۷۸"`` and ``"6362 1411 1234 5678"`` are all the same card number.
    """
    return _SEPARATORS.sub("", fold_digits(str(value or "")).strip())


def _digits_only(value: str, *, length: int, field: str, label: str) -> str:
    """The shared shape check: exactly ``length`` ASCII digits, or a message naming what was
    wrong. Length and non-digits are reported separately because they are different mistakes —
    a truncated copy-paste versus a value from the wrong column."""
    text = normalize(value)
    if not text:
        raise ZohalValidationError(f"{label} is required", field=field, value=text)
    if not text.isdigit():
        raise ZohalValidationError(
            f"{label} must be digits only; got {text!r}", field=field, value=text
        )
    if len(text) != length:
        raise ZohalValidationError(
            f"{label} must be {length} digits; got {len(text)}", field=field, value=text
        )
    return text


def check_national_code(value: Any, *, field: str = "national_code") -> str:
    """A personal national code (کد ملی): ten digits whose mod-11 check digit holds.

    Codes shorter than ten digits are left-padded with zeros, which is how they are issued and how
    they get lost — spreadsheets store them as numbers and drop the leading zeros. Padding here
    means a column that came back from Excel still works.

    Repeated-digit codes such as ``"1111111111"`` satisfy the checksum and are accepted. They are
    not real codes, but rejecting them means encoding a convention rather than the published
    algorithm, and a wrong rejection costs a caller their inquiry entirely — where letting one
    through costs a single call that Zohal answers with ``result=6``.
    """
    text = normalize(value)
    if text.isdigit() and 0 < len(text) < 10:
        text = text.zfill(10)
    text = _digits_only(text, length=10, field=field, label="national code")
    checksum = sum(int(text[i]) * (10 - i) for i in range(9)) % 11
    expected = checksum if checksum < 2 else 11 - checksum
    if int(text[9]) != expected:
        raise ZohalValidationError(
            f"national code {text!r} fails its check digit", field=field, value=text
        )
    return text


def check_national_id(value: Any, *, field: str = "national_id") -> str:
    """A company national id (شناسه ملی): eleven digits with their own weighted checksum.

    A different algorithm from the personal code above, on a different length — which is exactly
    why they are two functions. Passing a company id where a person is wanted fails on length
    before it can fail on anything subtler.
    """
    text = _digits_only(value, length=11, field=field, label="national id")
    prefix = int(text[9]) + 2
    weights = (29, 27, 19, 23, 31, 29, 27, 19, 23, 31)
    total = sum((int(text[i]) + prefix) * weights[i] for i in range(10))
    remainder = total % 11
    expected = 0 if remainder == 10 else remainder
    if int(text[10]) != expected:
        raise ZohalValidationError(
            f"national id {text!r} fails its check digit", field=field, value=text
        )
    return text


def check_iban(value: Any, *, field: str = "iban") -> str:
    """An Iranian IBAN (شبا): ``IR`` plus 24 digits, satisfying ISO 13616 mod-97.

    A bare 24 digits is accepted and prefixed — people copy the number out of a bank app without
    the country code more often than not.
    """
    text = normalize(value).upper()
    if text.startswith("IR"):
        body = text[2:]
    elif text.isdigit() and len(text) == 24:
        body = text
    else:
        raise ZohalValidationError(
            f"IBAN must start with IR and hold 24 digits; got {text!r}", field=field, value=text
        )
    if not body.isdigit() or len(body) != 24:
        raise ZohalValidationError(
            f"IBAN must hold 24 digits after IR; got {len(body)}", field=field, value=text
        )
    text = f"IR{body}"
    # ISO 13616: rotate the first four characters to the end, map letters to numbers, mod 97.
    rotated = text[4:] + "".join(_IBAN_LETTERS.get(c, c) for c in text[:4])
    if int(rotated) % 97 != 1:
        raise ZohalValidationError(f"IBAN {text!r} fails its checksum", field=field, value=text)
    return text


def check_card_number(value: Any, *, field: str = "card_number") -> str:
    """A bank card PAN: sixteen digits satisfying Luhn."""
    text = _digits_only(value, length=16, field=field, label="card number")
    total = 0
    for index, char in enumerate(reversed(text)):
        digit = int(char)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    if total % 10 != 0:
        raise ZohalValidationError(
            f"card number {text!r} fails its Luhn check", field=field, value=text
        )
    return text


def check_mobile(value: Any, *, field: str = "mobile") -> str:
    """An Iranian mobile number, normalised to ``09XXXXXXXXX``.

    Accepts every way one gets written down — ``+989121234567``, ``00989121234567``,
    ``989121234567``, ``9121234567`` — because a field that only takes one of them is a field
    users get wrong, and here they get it wrong at their own expense.
    """
    text = normalize(value).lstrip("+")
    if text.startswith("0098"):
        text = text[4:]
    elif text.startswith("98") and len(text) == 12:
        text = text[2:]
    if text.startswith("9") and len(text) == 10:
        text = f"0{text}"
    text = _digits_only(text, length=11, field=field, label="mobile number")
    if not text.startswith("09"):
        raise ZohalValidationError(
            f"mobile number must start with 09; got {text!r}", field=field, value=text
        )
    return text


def check_phone(value: Any, *, field: str = "phone_number") -> str:
    """A telephone number that may or may not be a mobile — digits, 8 to 12 of them.

    The fixed-line bill inquiry is the reason this is separate from :func:`check_mobile`. Zohal
    names that endpoint's field ``mobile`` and illustrates it with a mobile number, which is very
    likely copied from the three operator endpoints beside it. Requiring an ``09`` prefix there
    would reject a landline outright, and being wrong in that direction costs a caller the
    endpoint entirely — so the shape is checked and the prefix is not.
    """
    text = normalize(value).lstrip("+")
    if text.startswith("0098"):
        text = text[4:]
    if not text:
        raise ZohalValidationError("phone number is required", field=field, value=text)
    if not text.isdigit():
        raise ZohalValidationError(
            f"phone number must be digits only; got {text!r}", field=field, value=text
        )
    if not 8 <= len(text) <= 12:
        raise ZohalValidationError(
            f"phone number must be 8–12 digits; got {len(text)}", field=field, value=text
        )
    return text


def check_postal_code(value: Any, *, field: str = "postal_code") -> str:
    """A postal code: ten digits. Zohal accepts them without the conventional dash."""
    return _digits_only(value, length=10, field=field, label="postal code")


def check_sayad_id(value: Any, *, field: str = "sayad_id") -> str:
    """A Sayad cheque id (شناسه صیادی): the sixteen digits printed on the cheque."""
    return _digits_only(value, length=16, field=field, label="sayad id")


def check_birth_date(value: Any, *, field: str = "birth_date") -> str:
    """A Jalali birth date as ``YYYY/MM/DD``, which is the only format Zohal reads.

    Month lengths are enforced — 31 days in Farvardin through Shahrivar, 30 in Mehr through Bahman,
    at most 30 in Esfand. Esfand 30 is *not* rejected in a common year: which Jalali years are leap
    depends on which arithmetic approximation you pick, implementations disagree at the edges of
    the 33-year cycle, and a wrong answer here would reject a real person's real birthday. One
    ambiguous day slipping through to Zohal is the cheaper mistake.
    """
    text = fold_digits(str(value or "")).strip().replace("-", "/")
    match = re.fullmatch(r"(\d{4})/(\d{1,2})/(\d{1,2})", text)
    if not match:
        raise ZohalValidationError(
            f"birth date must be Jalali YYYY/MM/DD; got {text!r}", field=field, value=text
        )
    year, month, day = (int(part) for part in match.groups())
    if not 1 <= month <= 12:
        raise ZohalValidationError(
            f"birth date month must be 1–12; got {month}", field=field, value=text
        )
    longest = 31 if month <= 6 else 30
    if not 1 <= day <= longest:
        raise ZohalValidationError(
            f"birth date day must be 1–{longest} in month {month}; got {day}",
            field=field,
            value=text,
        )
    return f"{year:04d}/{month:02d}/{day:02d}"


def check_required(value: Any, *, field: str, label: str | None = None) -> str:
    """A free-text argument that only has to be present — a name, a website, a plate.

    Digits are folded but nothing is stripped: these are values where a space is meaningful, and
    ``"11 ب 111"`` is what a licence plate looks like.
    """
    text = fold_digits(str(value or "")).strip()
    if not text:
        raise ZohalValidationError(f"{label or field} is required", field=field, value=text)
    return text


def check_digits(value: Any, *, length: int, field: str, label: str) -> str:
    """A digit string of a fixed length that carries no checksum — a bank code, a region code."""
    return _digits_only(value, length=length, field=field, label=label)


def check_bill_id(value: Any, *, field: str = "bill_id") -> str:
    """A utility bill identifier (شناسه قبض): digits, of a length that varies by utility."""
    text = normalize(value)
    if not text:
        raise ZohalValidationError("bill id is required", field=field, value=text)
    if not text.isdigit():
        raise ZohalValidationError(
            f"bill id must be digits only; got {text!r}", field=field, value=text
        )
    return text


def as_int(value: Any) -> int | None:
    """An optional integer field, or ``None`` when Zohal omitted it or sent something else.

    Amounts arrive as numbers on some endpoints and as decimal *strings* on others — the vehicle
    inquiry reports ``"10000000"`` — so both are read the same way here.
    """
    if value is None or value == "":
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def as_text(value: Any) -> str | None:
    """An optional string field, stripped, or ``None`` when empty.

    Zohal fills fields it has nothing for with ``""`` rather than omitting them — the company
    inquiry's ``email_address`` and ``fax_number`` are usually empty strings — and an empty string
    is more usefully reported as absent.
    """
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def as_bool(value: Any) -> bool | None:
    """An optional boolean, or ``None`` when absent.

    ``"true"``/``"false"`` and ``1``/``0`` are read as well as real booleans, because ``matched``
    and ``is_transferable`` are not consistently typed across these endpoints.
    """
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def as_dict(value: Any) -> dict[str, Any]:
    """A nested object, or an empty dict when Zohal sent ``null`` or something that is not one."""
    if isinstance(value, dict):
        # JSON objects always have string keys; the cast tells a strict checker what `isinstance`
        # alone cannot, rather than letting `Unknown` leak into every record that reads a section.
        return cast("dict[str, Any]", value)
    return {}


def as_dicts(value: Any) -> list[dict[str, Any]]:
    """A list of objects, skipping anything in it that is not one.

    Zohal sends ``null`` rather than ``[]`` for empty collections on several endpoints — the
    credit report's ``bounced_cheques`` among them — so an empty list is the right answer for
    both.
    """
    if not isinstance(value, list):
        return []
    items: list[dict[str, Any]] = []
    for item in value:  # pyright: ignore[reportUnknownVariableType]
        if isinstance(item, dict):
            # JSON objects always have string keys; isinstance alone cannot say so.
            items.append(cast("dict[str, Any]", item))
    return items
