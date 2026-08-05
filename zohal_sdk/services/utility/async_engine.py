"""Utility services (خدماتی), async engine."""

from zohal_sdk.common.engine import AsyncEngine
from zohal_sdk.common.http import FileInput
from zohal_sdk.services.utility import constants as paths
from zohal_sdk.services.utility import helpers
from zohal_sdk.services.utility.constants import OCR_BACK_FIELD, OCR_FRONT_FIELD
from zohal_sdk.services.utility.data import (
    BoardMembers,
    Company,
    Enamad,
    Finglish,
    GasBill,
    MobileBill,
    NationalCardOcr,
    PostalAddress,
    UtilityBill,
    VehicleViolations,
    VehicleViolationsSummary,
    VoiceOtp,
)


class UtilityAsyncMixin(AsyncEngine):
    """The seventeen utility inquiries, on the async engine.

    Composed into :class:`~zohal_sdk.ZohalAsync`.
    """

    async def company_inquiry(self, national_id: str) -> Company:
        """A registered company by its eleven-digit national id (استعلام اطلاعات شرکت)."""
        answer = await self._inquiry(
            paths.COMPANY_INQUIRY, helpers.company_payload(national_id), service="company_inquiry"
        )
        return helpers.read_company(answer)

    async def company_board_members(self, national_id: str) -> BoardMembers:
        """A company's current board (استعلام اعضای هیئت‌مدیره شرکت)."""
        answer = await self._inquiry(
            paths.COMPANY_BOARD_MEMBERS,
            helpers.company_payload(national_id),
            service="company_board_members",
        )
        return helpers.read_board_members(answer)

    async def company_board_members_history(self, national_id: str) -> BoardMembers:
        """Everyone who has sat on a company's board (استعلام تاریخچه اعضای هیئت‌مدیره شرکت).

        The same record as the current-board inquiry, with
        :attr:`~zohal_sdk.services.utility.data.BoardMember.end_date` filled in.
        """
        answer = await self._inquiry(
            paths.COMPANY_BOARD_MEMBERS_HISTORY,
            helpers.company_payload(national_id),
            service="company_board_members_history",
        )
        return helpers.read_board_members(answer)

    async def postal_code_inquiry(self, postal_code: str) -> PostalAddress:
        """The address behind a ten-digit postal code (استعلام کد پستی)."""
        answer = await self._inquiry(
            paths.POSTAL_CODE_INQUIRY,
            helpers.postal_code_payload(postal_code),
            service="postal_code_inquiry",
        )
        return helpers.read_postal_address(answer)

    async def vehicle_total_violations(
        self, plate_number: str, region_code: str, national_code: str, mobile: str
    ) -> VehicleViolationsSummary:
        """What a vehicle owes in traffic fines, as a total (استعلام خلافی خودرو).

        ``plate_number`` is written the way it appears — ``"11 ب 111"`` — and ``region_code`` is
        the two-digit ایران number. The owner's ``national_code`` and a ``mobile`` are both
        required: the police system messages the result to that number as well as returning it.
        """
        answer = await self._inquiry(
            paths.VEHICLE_TOTAL_VIOLATIONS,
            helpers.vehicle_payload(plate_number, region_code, national_code, mobile),
            service="vehicle_total_violations",
        )
        return helpers.read_vehicle_summary(answer)

    async def vehicle_violations_details(
        self, plate_number: str, region_code: str, national_code: str, mobile: str
    ) -> VehicleViolations:
        """Every outstanding fine on a vehicle, itemised (استعلام خلافی خودرو با جزئیات)."""
        answer = await self._inquiry(
            paths.VEHICLE_VIOLATIONS_DETAILS,
            helpers.vehicle_payload(plate_number, region_code, national_code, mobile),
            service="vehicle_violations_details",
        )
        return helpers.read_vehicle_violations(answer)

    async def enamad_inquiry(self, website: str) -> Enamad:
        """A site's Enamad trust seal (استعلام Enamad). Falsy when there is none, or it expired."""
        answer = await self._inquiry(
            paths.ENAMAD_INQUIRY, helpers.enamad_payload(website), service="enamad_inquiry"
        )
        return helpers.read_enamad(answer)

    async def persian_to_finglish(self, persian_text: str) -> Finglish:
        """A Persian name transliterated to Latin script (تبدیل نام فارسی به فینگلیش)."""
        answer = await self._inquiry(
            paths.PERSIAN_TO_FINGLISH,
            helpers.finglish_payload(persian_text),
            service="persian_to_finglish",
        )
        return helpers.read_finglish(answer)

    async def national_card_ocr(
        self, national_card_front: FileInput, national_card_back: FileInput | None = None
    ) -> NationalCardOcr:
        """Read a national card's images (OCR کارت ملی).

        Each image is a path, raw ``bytes``, or an open binary file. The back is optional, and
        Zohal publishes no fields for it — see
        :attr:`~zohal_sdk.services.utility.data.NationalCardOcr.back`.
        """
        files: dict[str, FileInput] = {OCR_FRONT_FIELD: national_card_front}
        if national_card_back is not None:
            files[OCR_BACK_FIELD] = national_card_back
        answer = await self._inquiry_upload(
            paths.NATIONAL_CARD_OCR, files=files, service="national_card_ocr"
        )
        return helpers.read_national_card_ocr(answer)

    async def voice_otp(self, mobile: str, code: str) -> VoiceOtp:
        """Read a one-time code to someone over a phone call (OTP صوتی).

        Zohal publishes no response body for this endpoint, so the record carries its message and
        whatever else arrived rather than claiming a shape — see
        :class:`~zohal_sdk.services.utility.data.VoiceOtp`.
        """
        answer = await self._lenient(
            paths.VOICE_OTP, helpers.voice_otp_payload(mobile, code), service="voice_otp"
        )
        return helpers.read_voice_otp(answer)

    async def bill_mci(self, mobile: str) -> MobileBill:
        """A همراه اول bill (استعلام قبض همراه اول)."""
        answer = await self._inquiry(
            paths.BILL_MCI, helpers.mobile_bill_payload(mobile), service="bill_mci"
        )
        return helpers.read_mobile_bill(answer)

    async def bill_irancell(self, mobile: str) -> MobileBill:
        """An ایرانسل bill (استعلام قبض ایرانسل)."""
        answer = await self._inquiry(
            paths.BILL_IRANCELL, helpers.mobile_bill_payload(mobile), service="bill_irancell"
        )
        return helpers.read_mobile_bill(answer)

    async def bill_rightel(self, mobile: str) -> MobileBill:
        """A رایتل bill (استعلام قبض رایتل)."""
        answer = await self._inquiry(
            paths.BILL_RIGHTEL, helpers.mobile_bill_payload(mobile), service="bill_rightel"
        )
        return helpers.read_mobile_bill(answer)

    async def bill_fixed_line(self, phone_number: str) -> MobileBill:
        """A landline bill (استعلام قبض تلفن ثابت).

        Zohal names this endpoint's field ``mobile`` and illustrates it with a mobile number,
        which is almost certainly copied from the three operator endpoints. The number is checked
        for shape but not for an ``09`` prefix, so a landline goes through.
        """
        answer = await self._inquiry(
            paths.BILL_FIXED_LINE,
            helpers.fixed_line_bill_payload(phone_number),
            service="bill_fixed_line",
        )
        return helpers.read_mobile_bill(answer)

    async def bill_gas(self, bill_id: str) -> GasBill:
        """A gas bill by its شناسه قبض (استعلام قبض گاز)."""
        answer = await self._inquiry(
            paths.BILL_GAS, helpers.bill_payload(bill_id), service="bill_gas"
        )
        return helpers.read_gas_bill(answer)

    async def bill_water(self, bill_id: str) -> UtilityBill:
        """A water bill by its شناسه قبض (استعلام قبض آب)."""
        answer = await self._inquiry(
            paths.BILL_WATER, helpers.bill_payload(bill_id), service="bill_water"
        )
        return helpers.read_utility_bill(answer)

    async def bill_electricity(self, bill_id: str) -> UtilityBill:
        """An electricity bill by its شناسه قبض (استعلام قبض برق)."""
        answer = await self._inquiry(
            paths.BILL_ELECTRICITY, helpers.bill_payload(bill_id), service="bill_electricity"
        )
        return helpers.read_utility_bill(answer)
