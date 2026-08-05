"""Banking (بانکی) — ten endpoints, read against Zohal's own published examples."""

from collections.abc import Callable
from typing import Any

import pytest

from tests.conftest import (
    VALID_CARD,
    VALID_IBAN,
    VALID_NATIONAL_CODE,
    VALID_SAYAD_ID,
    FakeTransport,
)
from zohal_sdk import ZohalSync
from zohal_sdk.common.exceptions import ZohalValidationError

Example = Callable[..., dict[str, Any]]


class TestCardInquiries:
    def test_card_inquiry_reads_the_holder_name(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/card_inquiry"))
        record = sync_client.card_inquiry(VALID_CARD)
        assert record.name == "نام صاحب کارت"
        assert record.message == "موفق"

    def test_card_to_iban_reads_zohals_uppercase_key(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        # The response spells it IBAN; the /iban endpoint's request spells it iban.
        transport.reply(example("/services/inquiry/card_to_iban"))
        record = sync_client.card_to_iban(VALID_CARD)
        assert record.iban == "IRXXXXXXXXXXX"
        assert record.bank_name == "آینده"
        assert record.name == "نام صاحب کارت"

    def test_card_to_account(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/card_to_account"))
        record = sync_client.card_to_account(VALID_CARD)
        assert record.bank_account == "شماره حساب"
        assert record.bank_name == "نام بانک"

    def test_the_payload_carries_the_normalised_card_number(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/card_inquiry"))
        sync_client.card_inquiry("6362-1411-1234-5674")
        assert transport.payload == {"card_number": VALID_CARD}

    def test_an_invalid_card_is_refused_before_the_call_is_billed(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        with pytest.raises(ZohalValidationError):
            sync_client.card_inquiry("6362141112345678")
        assert transport.calls == []


class TestIbanInquiries:
    def test_iban_inquiry_uses_the_lowercase_request_key(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/iban"))
        record = sync_client.iban_inquiry(VALID_IBAN)
        assert record.bank_name == "آينده"
        assert record.is_transferable is True
        assert transport.payload == {"iban": VALID_IBAN}

    def test_account_to_iban_sends_both_parts(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/account_to_iban"))
        record = sync_client.account_to_iban("4600000123660", "062")
        assert record.iban == "IR700620000000XXX295898001"
        assert transport.payload == {"bank_account": "4600000123660", "bank_code": "062"}

    def test_a_bank_code_must_be_three_digits(self, sync_client: ZohalSync) -> None:
        with pytest.raises(ZohalValidationError, match="bank code"):
            sync_client.account_to_iban("4600000123660", "62")


class TestNameChecks:
    def test_check_iban_with_name_is_falsy_when_unmatched(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        transport.reply(
            {"result": 1, "response_body": {"data": {"matched": False}, "message": "موفق"}}
        )
        record = sync_client.check_iban_with_name(VALID_IBAN, "صادق بارانی")
        assert record.matched is False
        assert not record

    def test_check_iban_with_name_is_truthy_when_matched(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/check_iban_with_name"))
        assert sync_client.check_iban_with_name(VALID_IBAN, "صادق بارانی")

    def test_an_absent_verdict_never_reads_as_a_match(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        transport.reply({"result": 1, "response_body": {"data": {}, "message": "موفق"}})
        assert not sync_client.check_iban_with_name(VALID_IBAN, "صادق بارانی")

    def test_check_card_with_name_returns_the_holder_name(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        # Zohal documents no verdict on this one, only the name — so matched stays None.
        transport.reply(example("/services/inquiry/check_card_with_name"))
        record = sync_client.check_card_with_name(VALID_CARD, "محمد صادقی")
        assert record.name == "نام صاحب کارت"
        assert record.matched is None

    def test_the_iban_name_check_sends_the_uppercase_key(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/check_iban_with_name"))
        sync_client.check_iban_with_name(VALID_IBAN, "صادق بارانی")
        assert set(transport.payload) == {"IBAN", "name"}


class TestCheques:
    def test_sayad_cheque_reads_every_documented_field(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/check_sayad_inquiry"))
        record = sync_client.sayad_cheque(VALID_SAYAD_ID)
        assert record.check_type == "BANS"
        assert record.issue_date == "1370/1/1"
        assert record.serial_no == "95XXX1"
        # An empty string in the payload is reported as absent, not as "".
        assert record.returned_cheques is None

    def test_the_transfer_chain_keeps_zohals_order(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/check_sayad_inquiry/chain"))
        record = sync_client.sayad_cheque_chain(VALID_SAYAD_ID, VALID_NATIONAL_CODE)
        assert [link.role_type for link in record.links] == [1, 2, 3]
        assert record.links[0].customers[0].name == "نام فرد یا شرکت"

    def test_a_chain_customer_type_is_decoded_beside_its_raw_value(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/check_sayad_inquiry/chain"))
        customer = (
            sync_client.sayad_cheque_chain(VALID_SAYAD_ID, VALID_NATIONAL_CODE)
            .links[0]
            .customers[0]
        )
        assert customer.customer_type == 1
        assert customer.customer_type_text == "حقیقی"

    def test_bounced_cheque_is_falsy_when_there_are_none(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/bounced_cheque"))
        record = sync_client.bounced_cheque(VALID_NATIONAL_CODE)
        assert record.count == 0
        assert not record

    def test_bounced_cheque_is_truthy_when_there_are_some(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        transport.reply({"result": 1, "response_body": {"data": {"count": 3}, "message": "موفق"}})
        assert sync_client.bounced_cheque(VALID_NATIONAL_CODE)

    def test_bounced_cheque_defaults_to_the_iranian_nationality_type(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/bounced_cheque"))
        sync_client.bounced_cheque(VALID_NATIONAL_CODE)
        assert transport.payload["nationality_type"] == 1
