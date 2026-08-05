"""The input checks — the half of the SDK that runs before anything is billed."""

import pytest

from zohal_sdk.common.exceptions import ZohalValidationError
from zohal_sdk.common.utils import (
    as_bool,
    as_dicts,
    as_int,
    as_text,
    check_birth_date,
    check_card_number,
    check_iban,
    check_mobile,
    check_national_code,
    check_national_id,
    check_phone,
    fold_digits,
    normalize,
)


class TestNormalisation:
    def test_persian_digits_fold_to_ascii(self) -> None:
        assert fold_digits("۰۹۱۲۱۲۳۴۵۶۷") == "09121234567"

    def test_arabic_indic_digits_fold_to_ascii(self) -> None:
        assert fold_digits("٠٩١٢١٢٣٤٥٦٧") == "09121234567"

    def test_mixed_scripts_in_one_value(self) -> None:
        assert fold_digits("۰۹١٢1234567") == "09121234567"

    @pytest.mark.parametrize(
        "written",
        ["6362-1411-1234-5674", "6362 1411 1234 5674", "6362_1411.1234.5674"],
    )
    def test_separators_are_stripped(self, written: str) -> None:
        assert normalize(written) == "6362141112345674"


class TestNationalCode:
    def test_accepts_a_valid_code(self) -> None:
        assert check_national_code("0013542419") == "0013542419"

    def test_folds_and_accepts_persian_digits(self) -> None:
        assert check_national_code("۰۰۱۳۵۴۲۴۱۹") == "0013542419"

    def test_pads_a_code_excel_stripped_leading_zeros_from(self) -> None:
        assert check_national_code("13542419") == "0013542419"

    def test_rejects_a_bad_check_digit(self) -> None:
        with pytest.raises(ZohalValidationError) as caught:
            check_national_code("0013542418")
        assert caught.value.field == "national_code"
        assert "check digit" in str(caught.value)

    def test_rejects_non_digits(self) -> None:
        with pytest.raises(ZohalValidationError):
            check_national_code("00135424XY")

    def test_rejects_an_empty_value(self) -> None:
        with pytest.raises(ZohalValidationError):
            check_national_code("")


class TestNationalId:
    def test_accepts_a_valid_company_id(self) -> None:
        assert check_national_id("10103640187") == "10103640187"

    def test_rejects_a_bad_check_digit(self) -> None:
        with pytest.raises(ZohalValidationError):
            check_national_id("10103640188")

    def test_rejects_a_personal_code_on_length(self) -> None:
        # Ten digits where eleven are wanted — caught before any subtler check.
        with pytest.raises(ZohalValidationError, match="11 digits"):
            check_national_id("0013542419")


class TestIban:
    def test_accepts_a_valid_iban(self) -> None:
        assert check_iban("IR820540102680020817909002") == "IR820540102680020817909002"

    def test_accepts_it_written_out_in_groups(self) -> None:
        assert check_iban("IR82 0540 1026 8002 0817 9090 02") == "IR820540102680020817909002"

    def test_adds_the_country_code_when_omitted(self) -> None:
        assert check_iban("820540102680020817909002") == "IR820540102680020817909002"

    def test_rejects_a_failed_checksum(self) -> None:
        with pytest.raises(ZohalValidationError, match="checksum"):
            check_iban("IR820540102680020817909003")

    def test_rejects_the_wrong_length(self) -> None:
        with pytest.raises(ZohalValidationError):
            check_iban("IR8205401026800208179090")


class TestCardNumber:
    def test_accepts_a_luhn_valid_pan(self) -> None:
        assert check_card_number("6362141112345674") == "6362141112345674"

    def test_rejects_a_luhn_failure(self) -> None:
        with pytest.raises(ZohalValidationError, match="Luhn"):
            check_card_number("6362141112345678")

    def test_rejects_a_short_pan(self) -> None:
        with pytest.raises(ZohalValidationError, match="16 digits"):
            check_card_number("63621411123456")


class TestMobile:
    @pytest.mark.parametrize(
        "written",
        ["09121234567", "+989121234567", "00989121234567", "989121234567", "9121234567"],
    )
    def test_every_way_it_gets_written_normalises_the_same(self, written: str) -> None:
        assert check_mobile(written) == "09121234567"

    def test_rejects_a_landline(self) -> None:
        with pytest.raises(ZohalValidationError):
            check_mobile("02191097734")


class TestPhone:
    def test_accepts_a_landline_for_the_fixed_line_bill(self) -> None:
        assert check_phone("021-9109-7734") == "02191097734"

    def test_accepts_a_mobile_too(self) -> None:
        assert check_phone("09121234567") == "09121234567"

    def test_rejects_letters(self) -> None:
        with pytest.raises(ZohalValidationError):
            check_phone("021911CALL")


class TestBirthDate:
    def test_pads_a_jalali_date(self) -> None:
        assert check_birth_date("1377/7/9") == "1377/07/09"

    def test_accepts_dashes(self) -> None:
        assert check_birth_date("1377-07-19") == "1377/07/19"

    def test_folds_persian_digits(self) -> None:
        assert check_birth_date("۱۳۷۷/۰۷/۱۹") == "1377/07/19"

    def test_rejects_a_31st_in_the_second_half_of_the_year(self) -> None:
        with pytest.raises(ZohalValidationError, match="1–30"):
            check_birth_date("1377/08/31")

    def test_allows_a_31st_in_the_first_half(self) -> None:
        assert check_birth_date("1377/03/31") == "1377/03/31"

    def test_rejects_a_bad_month(self) -> None:
        with pytest.raises(ZohalValidationError, match="1–12"):
            check_birth_date("1377/13/01")

    def test_rejects_a_gregorian_date(self) -> None:
        with pytest.raises(ZohalValidationError):
            check_birth_date("1998-10-11T00:00:00Z")

    def test_allows_esfand_30_since_the_leap_rule_is_not_worth_guessing(self) -> None:
        # Deliberate: rejecting this would need a Jalali leap rule that implementations disagree
        # on, and being wrong would reject a real birthday. See check_birth_date's docstring.
        assert check_birth_date("1377/12/30") == "1377/12/30"


class TestCoercions:
    @pytest.mark.parametrize(
        ("given", "expected"),
        [(1000, 1000), ("1000", 1000), (" 1000 ", 1000), ("", None), (None, None), ("abc", None)],
    )
    def test_as_int(self, given: object, expected: int | None) -> None:
        assert as_int(given) == expected

    @pytest.mark.parametrize(
        ("given", "expected"),
        [("موفق", "موفق"), ("  x  ", "x"), ("", None), (None, None)],
    )
    def test_as_text(self, given: object, expected: str | None) -> None:
        assert as_text(given) == expected

    @pytest.mark.parametrize(
        ("given", "expected"),
        [(True, True), (False, False), ("true", True), ("0", False), (1, True), ("", None)],
    )
    def test_as_bool(self, given: object, expected: bool | None) -> None:
        assert as_bool(given) == expected

    def test_as_dicts_treats_null_as_empty(self) -> None:
        # Zohal sends null rather than [] for empty collections on several endpoints.
        assert as_dicts(None) == []

    def test_as_dicts_skips_non_objects(self) -> None:
        assert as_dicts([{"a": 1}, "junk", None]) == [{"a": 1}]
