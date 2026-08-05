"""Utility services (خدماتی) — companies, addresses, vehicles, Enamad, OCR and the bills."""

from collections.abc import Callable
from typing import Any

import pytest

from tests.conftest import (
    VALID_MOBILE,
    VALID_NATIONAL_CODE,
    VALID_NATIONAL_ID,
    VALID_POSTAL_CODE,
    FakeTransport,
    envelope,
)
from zohal_sdk import ZohalSync
from zohal_sdk.common.exceptions import ZohalValidationError

Example = Callable[..., dict[str, Any]]


class TestCompanies:
    def test_company_inquiry(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/company_inquiry"))
        record = sync_client.company_inquiry(VALID_NATIONAL_ID)
        assert record.name == "راهکار نوین هیوا"
        assert record.company_type == "شرکت سهامی خاص"
        assert record.register_number == "43XXX0"
        # Zohal fills these with "" rather than omitting them.
        assert record.email_address is None
        assert record.fax_number is None

    def test_a_company_id_that_fails_its_checksum_is_refused_locally(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        with pytest.raises(ZohalValidationError, match="national id"):
            sync_client.company_inquiry("10103640188")
        assert transport.calls == []

    def test_current_board(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/company_inquiry/board_members"))
        record = sync_client.company_board_members(VALID_NATIONAL_ID)
        assert record.company_title == "نام شرکت"
        assert record.members[0].position == "بازرس اصلی"
        assert record.members[0].end_date is None

    def test_board_history_carries_end_dates(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/company_inquiry/board_members/history"))
        record = sync_client.company_board_members_history(VALID_NATIONAL_ID)
        assert record.members[0].end_date == "1399/01/01"
        assert record.members[0].position == "مدیر عامل"


class TestPostalCode:
    def test_the_nested_address_is_lifted_to_the_top(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/postal_code_inquiry"))
        record = sync_client.postal_code_inquiry(VALID_POSTAL_CODE)
        assert record.province == "تهران"
        assert record.street == "خیابان 12 فروردین"
        assert record.number == 1302
        # A basement floor is a string, not a number.
        assert record.floor == "-1"


class TestVehicles:
    def test_total_violations_reads_string_amounts_as_integers(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/vehicle_inquiry/total_violations"))
        record = sync_client.vehicle_total_violations(
            "11 ب 111", "11", VALID_NATIONAL_CODE, VALID_MOBILE
        )
        assert record.inquire_price == 10_000_000
        assert record.warning_price == 10_000_000

    def test_the_plate_keeps_its_persian_letter_and_spacing(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/vehicle_inquiry/total_violations"))
        sync_client.vehicle_total_violations("11 ب 111", "11", VALID_NATIONAL_CODE, VALID_MOBILE)
        assert transport.payload["plate_number"] == "11 ب 111"

    def test_itemised_violations_flatten_zohals_nested_one_key_objects(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/vehicle_inquiry/violations_details"))
        record = sync_client.vehicle_violations_details(
            "11 ب 111", "11", VALID_NATIONAL_CODE, VALID_MOBILE
        )
        first = record.violations[0]
        assert first.violation_type == "همراه نداشتن گواهي يا برچسب معتبر معاينه فني"
        assert first.violation_type_id == "2163"
        assert first.delivery_type == "تسليمي"

    def test_the_misspelled_address_key_is_read(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        # Zohal spells it `violatoin_address`.
        transport.reply(example("/services/inquiry/vehicle_inquiry/violations_details"))
        record = sync_client.vehicle_violations_details(
            "11 ب 111", "11", VALID_NATIONAL_CODE, VALID_MOBILE
        )
        assert record.violations[0].address == "تهران بزرگراه يادگار"

    def test_the_itemised_total_is_summed_locally(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/vehicle_inquiry/violations_details"))
        record = sync_client.vehicle_violations_details(
            "11 ب 111", "11", VALID_NATIONAL_CODE, VALID_MOBILE
        )
        assert record.total == 500_000


class TestEnamadAndFinglish:
    def test_a_live_seal_is_truthy(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/enamad_inquiry"))
        record = sync_client.enamad_inquiry("digikala.com")
        assert record.logo_level == 4
        assert record.expired is False
        assert record

    def test_enamads_verdict_is_kept_apart_from_zohals_message(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/enamad_inquiry"))
        record = sync_client.enamad_inquiry("digikala.com")
        assert record.status_message == "نماد دارد."
        assert record.message == "موفق"

    def test_an_expired_seal_is_falsy(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        transport.reply(envelope({"id": 19077, "expired": True}))
        assert not sync_client.enamad_inquiry("example.com")

    def test_persian_to_finglish(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/persian_to_finglish"))
        assert sync_client.persian_to_finglish("حمید").finglish_text == "mohammad naderi"


class TestNationalCardOcr:
    def test_the_front_is_read_into_a_record(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/national_card_ocr"))
        record = sync_client.national_card_ocr(b"front-image-bytes")
        assert record.front is not None
        assert record.front.national_code == "0370362063"
        assert record.front.last_name == "متقی زاده"
        assert record.front.result is True

    def test_the_undocumented_back_passes_through_as_a_dict(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/national_card_ocr"))
        assert sync_client.national_card_ocr(b"front").back == {}

    def test_the_back_image_is_optional_and_omitted_when_not_given(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/national_card_ocr"))
        sync_client.national_card_ocr(b"front")
        assert transport.call.files is not None
        assert set(transport.call.files) == {"national_card_front"}

    def test_both_images_are_sent_when_both_are_given(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/national_card_ocr"))
        sync_client.national_card_ocr(b"front", b"back")
        assert transport.call.files is not None
        assert set(transport.call.files) == {"national_card_front", "national_card_back"}


class TestVoiceOtp:
    def test_an_undocumented_response_is_accepted(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        # Zohal publishes no response body for this endpoint at all.
        transport.reply({"sent": True})
        record = sync_client.voice_otp(VALID_MOBILE, "89129")
        assert record.data == {"sent": True}

    def test_a_result_code_is_still_honoured_when_one_arrives(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        transport.reply(envelope({}, result=6, message="شماره نامعتبر"), status=400)
        with pytest.raises(Exception, match="شماره نامعتبر"):
            sync_client.voice_otp(VALID_MOBILE, "89129")


class TestBills:
    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("bill_mci", "/services/inquiry/bill/mci"),
            ("bill_irancell", "/services/inquiry/bill/irancell"),
            ("bill_rightel", "/services/inquiry/bill/rightel"),
        ],
    )
    def test_every_operator_bill_reads_both_terms(
        self,
        sync_client: ZohalSync,
        transport: FakeTransport,
        example: Example,
        method: str,
        path: str,
    ) -> None:
        transport.reply(example(path))
        record = getattr(sync_client, method)(VALID_MOBILE)
        assert record.mid_term is not None
        assert record.final_term is not None
        assert record.mid_term.amount == 1000

    def test_the_fixed_line_bill_accepts_a_landline(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        # Zohal names the field `mobile` here; a landline must still go through.
        transport.reply(example("/services/inquiry/bill/fixed_line"))
        sync_client.bill_fixed_line("02191097734")
        assert transport.payload == {"mobile": "02191097734"}

    def test_gas_bill_has_its_own_meter_reading_fields(
        self, sync_client: ZohalSync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(example("/services/inquiry/bill/gas"))
        record = sync_client.bill_gas("123456789")
        assert record.amount == 100_000
        # Zohal's example has a leading space here; as_text strips it.
        assert record.consumption_type == "خانگي بدون چیلر"
        assert record.current_reading_date == "1304/09/11"

    @pytest.mark.parametrize(
        ("method", "path", "account_type"),
        [
            ("bill_water", "/services/inquiry/bill/water", "مسکونی"),
            ("bill_electricity", "/services/inquiry/bill/electricity", "خانگی"),
        ],
    )
    def test_water_and_electricity_share_a_record(
        self,
        sync_client: ZohalSync,
        transport: FakeTransport,
        example: Example,
        method: str,
        path: str,
        account_type: str,
    ) -> None:
        transport.reply(example(path))
        record = getattr(sync_client, method)("123456789012")
        assert record.account_type == account_type
        assert record.full_name == "نام مالک"

    def test_a_non_numeric_bill_id_is_refused_locally(
        self, sync_client: ZohalSync, transport: FakeTransport
    ) -> None:
        with pytest.raises(ZohalValidationError, match="bill id"):
            sync_client.bill_gas("not-a-bill")
        assert transport.calls == []
