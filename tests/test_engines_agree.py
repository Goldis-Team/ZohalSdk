"""Both engines, over the same fixtures, must produce the same records.

The whole reason each family splits into ``helpers.py`` plus two thin engines is that the sync and
async paths cannot then drift apart. This module is what holds that claim to account: every
endpoint is driven through :class:`~zohal_sdk.ZohalSync` and :class:`~zohal_sdk.ZohalAsync` against
the same published example, and the two records must compare equal — which they do only if both
engines built the same payload and read the response the same way.

It also catches the failure the async engines are generated to avoid: a missing ``await`` leaves a
coroutine where a record should be, and a coroutine never equals a dataclass.
"""

import asyncio
from collections.abc import Callable
from typing import Any

import pytest

from tests.conftest import (
    TOKEN,
    VALID_BIRTH_DATE,
    VALID_CARD,
    VALID_IBAN,
    VALID_MOBILE,
    VALID_NATIONAL_CODE,
    VALID_NATIONAL_ID,
    VALID_POSTAL_CODE,
    VALID_SAYAD_ID,
    FakeTransport,
)
from zohal_sdk import ZohalAsync, ZohalSync

Example = Callable[..., dict[str, Any]]

#: ``(method name, path of the published example, positional arguments)`` for every endpoint that
#: has one. The three with no published response are covered in their own modules.
ENDPOINTS: list[tuple[str, str, tuple[Any, ...]]] = [
    ("card_inquiry", "/services/inquiry/card_inquiry", (VALID_CARD,)),
    ("card_to_iban", "/services/inquiry/card_to_iban", (VALID_CARD,)),
    ("card_to_account", "/services/inquiry/card_to_account", (VALID_CARD,)),
    ("account_to_iban", "/services/inquiry/account_to_iban", ("4600000123660", "062")),
    ("iban_inquiry", "/services/inquiry/iban", (VALID_IBAN,)),
    ("check_card_with_name", "/services/inquiry/check_card_with_name", (VALID_CARD, "محمد صادقی")),
    ("check_iban_with_name", "/services/inquiry/check_iban_with_name", (VALID_IBAN, "صادق بارانی")),
    ("sayad_cheque", "/services/inquiry/check_sayad_inquiry", (VALID_SAYAD_ID,)),
    (
        "sayad_cheque_chain",
        "/services/inquiry/check_sayad_inquiry/chain",
        (VALID_SAYAD_ID, VALID_NATIONAL_CODE),
    ),
    ("bounced_cheque", "/services/inquiry/bounced_cheque", (VALID_NATIONAL_CODE,)),
    ("shahkar", "/services/inquiry/shahkar", (VALID_NATIONAL_CODE, VALID_MOBILE)),
    (
        "national_identity",
        "/services/inquiry/national_identity_inquiry",
        (VALID_NATIONAL_CODE, VALID_BIRTH_DATE),
    ),
    (
        "check_iban_with_national_code",
        "/services/inquiry/check_iban_with_national_code",
        (VALID_IBAN, VALID_NATIONAL_CODE, VALID_BIRTH_DATE),
    ),
    (
        "check_card_with_national_code",
        "/services/inquiry/check_card_with_national_code",
        (VALID_CARD, VALID_NATIONAL_CODE, VALID_BIRTH_DATE),
    ),
    ("company_inquiry", "/services/inquiry/company_inquiry", (VALID_NATIONAL_ID,)),
    (
        "company_board_members",
        "/services/inquiry/company_inquiry/board_members",
        (VALID_NATIONAL_ID,),
    ),
    (
        "company_board_members_history",
        "/services/inquiry/company_inquiry/board_members/history",
        (VALID_NATIONAL_ID,),
    ),
    ("postal_code_inquiry", "/services/inquiry/postal_code_inquiry", (VALID_POSTAL_CODE,)),
    (
        "vehicle_total_violations",
        "/services/inquiry/vehicle_inquiry/total_violations",
        ("11 ب 111", "11", VALID_NATIONAL_CODE, VALID_MOBILE),
    ),
    (
        "vehicle_violations_details",
        "/services/inquiry/vehicle_inquiry/violations_details",
        ("11 ب 111", "11", VALID_NATIONAL_CODE, VALID_MOBILE),
    ),
    ("enamad_inquiry", "/services/inquiry/enamad_inquiry", ("zohal.io",)),
    ("persian_to_finglish", "/services/inquiry/persian_to_finglish", ("حمید",)),
    ("national_card_ocr", "/services/inquiry/national_card_ocr", (b"front-bytes",)),
    ("bill_mci", "/services/inquiry/bill/mci", (VALID_MOBILE,)),
    ("bill_irancell", "/services/inquiry/bill/irancell", (VALID_MOBILE,)),
    ("bill_rightel", "/services/inquiry/bill/rightel", (VALID_MOBILE,)),
    ("bill_fixed_line", "/services/inquiry/bill/fixed_line", ("02191097734",)),
    ("bill_gas", "/services/inquiry/bill/gas", ("123456789",)),
    ("bill_water", "/services/inquiry/bill/water", ("123456789012",)),
    ("bill_electricity", "/services/inquiry/bill/electricity", ("123456789012",)),
    ("upload_biometric_media", "/services/biometric/media/", (b"video-bytes",)),
    (
        "start_liveness",
        "/services/biometric/session/liveness/",
        (VALID_NATIONAL_CODE, VALID_BIRTH_DATE, "1G34567890", "a271d113-video-uuid"),
    ),
    ("biometric_result", "/services/biometric/session/{id}/result", ("session-uuid",)),
    (
        "credit_send_otp",
        "/services/inquiry/credit_inquiry/send_otp",
        (VALID_NATIONAL_CODE, VALID_MOBILE),
    ),
    (
        "credit_result",
        "/services/inquiry/credit_inquiry/result/{reference_id}",
        ("reference-id",),
    ),
]


def test_the_table_covers_every_endpoint_with_a_published_example(
    examples: dict[str, dict[str, Any]],
) -> None:
    """A new endpoint added without a row here would silently escape this whole module."""
    covered = {path for _, path, _ in ENDPOINTS}
    assert covered == set(examples), f"uncovered: {sorted(set(examples) - covered)}"


@pytest.mark.parametrize(("method", "path", "args"), ENDPOINTS, ids=[e[0] for e in ENDPOINTS])
def test_both_engines_produce_the_same_record(
    transport: FakeTransport,
    example: Example,
    method: str,
    path: str,
    args: tuple[Any, ...],
) -> None:
    body = example(path)

    transport.reply(body)
    from_sync = getattr(ZohalSync(token=TOKEN), method)(*args)
    sync_call = transport.calls.pop()

    transport.queue.clear()
    transport.reply(body)
    from_async = asyncio.run(getattr(ZohalAsync(token=TOKEN), method)(*args))
    async_call = transport.calls.pop()

    assert from_sync == from_async
    assert sync_call == async_call
