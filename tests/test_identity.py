"""Identity (احراز هویت) — Shahkar, the civil registry, and the identity-to-bank checks."""

from collections.abc import Callable
from typing import Any

import pytest

from tests.conftest import (
    VALID_BIRTH_DATE,
    VALID_CARD,
    VALID_IBAN,
    VALID_MOBILE,
    VALID_NATIONAL_CODE,
    FakeTransport,
)
from zohal_sdk import ZohalSync
from zohal_sdk.common.exceptions import ZohalServiceError, ZohalValidationError

Example = Callable[..., dict[str, Any]]


class TestShahkar:
    def test_a_match_is_truthy(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/shahkar"))
        assert sync_client.shahkar(VALID_NATIONAL_CODE, VALID_MOBILE)

    def test_a_mismatch_is_a_successful_inquiry_not_an_error(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        # The SIM not belonging to the person is an answer, and must not raise.
        transport.reply(
            {"result": 1, "response_body": {"data": {"matched": False}, "message": "موفق"}}
        )
        record = sync_client.shahkar(VALID_NATIONAL_CODE, VALID_MOBILE)
        assert not record
        assert record.matched is False

    def test_zohals_own_400_still_raises(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/shahkar", "400"), status=400)
        with pytest.raises(ZohalServiceError) as caught:
            sync_client.shahkar(VALID_NATIONAL_CODE, VALID_MOBILE)
        assert caught.value.result == 6
        assert caught.value.error_code == "invalid"

    def test_the_mobile_is_normalised_on_the_way_out(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/shahkar"))
        sync_client.shahkar(VALID_NATIONAL_CODE, "+989121234567")
        assert transport.payload["mobile"] == VALID_MOBILE


class TestNationalIdentity:
    def test_reads_the_person(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/national_identity_inquiry"))
        record = sync_client.national_identity(VALID_NATIONAL_CODE, VALID_BIRTH_DATE)
        assert record.first_name == "نام"
        assert record.last_name == "نام خانوادگی"
        assert record.father_name == "نام پدر"
        assert record.matched is True
        assert record

    def test_both_liveness_fields_are_reported_rather_than_reconciled(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/national_identity_inquiry"))
        record = sync_client.national_identity(VALID_NATIONAL_CODE, VALID_BIRTH_DATE)
        assert record.alive is True
        assert record.is_dead is False

    def test_an_unmatched_person_is_falsy(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        transport.reply(
            {"result": 1, "response_body": {"data": {"matched": False}, "message": "موفق"}}
        )
        assert not sync_client.national_identity(VALID_NATIONAL_CODE, VALID_BIRTH_DATE)

    def test_an_invalid_jalali_date_is_refused_locally(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        with pytest.raises(ZohalValidationError, match="birth date"):
            sync_client.national_identity(VALID_NATIONAL_CODE, "1377/13/45")
        assert transport.calls == []


class TestIdentityToBankChecks:
    def test_iban_against_national_code(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/check_iban_with_national_code"))
        assert sync_client.check_iban_with_national_code(
            VALID_IBAN, VALID_NATIONAL_CODE, VALID_BIRTH_DATE
        )
        assert set(transport.payload) == {"IBAN", "national_code", "birth_date"}

    def test_card_against_national_code(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/check_card_with_national_code"))
        assert sync_client.check_card_with_national_code(
            VALID_CARD, VALID_NATIONAL_CODE, VALID_BIRTH_DATE
        )
        assert set(transport.payload) == {"card_number", "national_code", "birth_date"}
