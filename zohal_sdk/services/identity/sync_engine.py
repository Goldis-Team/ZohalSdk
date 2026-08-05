"""Identity (احراز هویت), sync engine."""

from zohal_sdk.common.data import MatchResult
from zohal_sdk.common.engine import SyncEngine
from zohal_sdk.services.identity import constants as paths
from zohal_sdk.services.identity import helpers
from zohal_sdk.services.identity.data import NationalIdentity


class IdentitySyncMixin(SyncEngine):
    """The four identity checks, on the sync engine.

    Composed into :class:`~zohal_sdk.ZohalSync`.
    """

    def shahkar(self, national_code: str, mobile: str) -> MatchResult:
        """Whether a mobile number is registered to a national code (شاهکار).

        The standard check before trusting an OTP: it proves the SIM belongs to the person whose
        identity you are about to accept. Falsy when unmatched.
        """
        answer = self._inquiry(
            paths.SHAHKAR, helpers.shahkar_payload(national_code, mobile), service="shahkar"
        )
        return helpers.read_match(answer)

    def national_identity(self, national_code: str, birth_date: str) -> NationalIdentity:
        """A person from the civil registry (استعلام اطلاعات هویتی).

        ``birth_date`` is Jalali, ``YYYY/MM/DD``. The record is falsy when the code and the date
        do not identify the same person, and the name fields mean nothing in that case.
        """
        answer = self._inquiry(
            paths.NATIONAL_IDENTITY,
            helpers.national_identity_payload(national_code, birth_date),
            service="national_identity",
        )
        return helpers.read_national_identity(answer)

    def check_iban_with_national_code(
        self, iban: str, national_code: str, birth_date: str
    ) -> MatchResult:
        """Whether an IBAN belongs to a person (تطابق کد ملی و شماره شبا). Falsy when unmatched."""
        answer = self._inquiry(
            paths.CHECK_IBAN_WITH_NATIONAL_CODE,
            helpers.iban_with_national_code_payload(iban, national_code, birth_date),
            service="check_iban_with_national_code",
        )
        return helpers.read_match(answer)

    def check_card_with_national_code(
        self, card_number: str, national_code: str, birth_date: str
    ) -> MatchResult:
        """Whether a card belongs to a person (تطابق شماره کارت و کد ملی). Falsy when unmatched."""
        answer = self._inquiry(
            paths.CHECK_CARD_WITH_NATIONAL_CODE,
            helpers.card_with_national_code_payload(card_number, national_code, birth_date),
            service="check_card_with_national_code",
        )
        return helpers.read_match(answer)
