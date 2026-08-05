"""Banking (بانکی), sync engine."""

from zohal_sdk.common.data import MatchResult
from zohal_sdk.common.engine import SyncEngine
from zohal_sdk.services.banking import constants as paths
from zohal_sdk.services.banking import helpers
from zohal_sdk.services.banking.constants import CHEQUE_TYPE_SAYADI, NATIONALITY_IRANIAN
from zohal_sdk.services.banking.data import (
    AccountToIban,
    BouncedCheque,
    CardHolder,
    CardNameMatch,
    CardToAccount,
    CardToIban,
    IbanInfo,
    SayadCheque,
    SayadChequeChain,
)


class BankingSyncMixin(SyncEngine):
    """The ten banking inquiries, on the sync engine.

    Composed into :class:`~zohal_sdk.ZohalSync`; usable on its own if banking is all you need.
    """

    def card_inquiry(self, card_number: str) -> CardHolder:
        """The name on a card (استعلام نام صاحب کارت)."""
        answer = self._inquiry(
            paths.CARD_INQUIRY, helpers.card_payload(card_number), service="card_inquiry"
        )
        return helpers.read_card_holder(answer)

    def card_to_iban(self, card_number: str) -> CardToIban:
        """A card number resolved to its IBAN (تبدیل کارت به شبا)."""
        answer = self._inquiry(
            paths.CARD_TO_IBAN, helpers.card_payload(card_number), service="card_to_iban"
        )
        return helpers.read_card_to_iban(answer)

    def card_to_account(self, card_number: str) -> CardToAccount:
        """A card number resolved to its account number (تبدیل کارت به حساب)."""
        answer = self._inquiry(
            paths.CARD_TO_ACCOUNT, helpers.card_payload(card_number), service="card_to_account"
        )
        return helpers.read_card_to_account(answer)

    def account_to_iban(self, bank_account: str, bank_code: str) -> AccountToIban:
        """An account number resolved to its IBAN (تبدیل حساب به شبا).

        ``bank_code`` is the three-digit code for the account's bank, e.g. ``"062"``.
        """
        answer = self._inquiry(
            paths.ACCOUNT_TO_IBAN,
            helpers.account_payload(bank_account, bank_code),
            service="account_to_iban",
        )
        return helpers.read_account_to_iban(answer)

    def iban_inquiry(self, iban: str) -> IbanInfo:
        """Who an IBAN belongs to, and whether it can receive a transfer (استعلام شبا)."""
        answer = self._inquiry(
            paths.IBAN_INQUIRY, helpers.iban_payload(iban), service="iban_inquiry"
        )
        return helpers.read_iban_info(answer)

    def check_card_with_name(self, card_number: str, name: str) -> CardNameMatch:
        """A card checked against a name (تطابق کارت و نام صاحب کارت).

        Zohal answers with the holder's name rather than a verdict — see
        :class:`~zohal_sdk.services.banking.data.CardNameMatch`.
        """
        answer = self._inquiry(
            paths.CHECK_CARD_WITH_NAME,
            helpers.card_with_name_payload(card_number, name),
            service="check_card_with_name",
        )
        return helpers.read_card_name_match(answer)

    def check_iban_with_name(self, iban: str, name: str) -> MatchResult:
        """An IBAN checked against a name (تطابق شبا و نام صاحب شبا). Falsy when unmatched."""
        answer = self._inquiry(
            paths.CHECK_IBAN_WITH_NAME,
            helpers.iban_with_name_payload(iban, name),
            service="check_iban_with_name",
        )
        return helpers.read_match(answer)

    def sayad_cheque(self, sayad_id: str) -> SayadCheque:
        """A Sayad cheque, by the sixteen-digit id printed on it (استعلام چک صیادی)."""
        answer = self._inquiry(
            paths.SAYAD_CHEQUE, helpers.sayad_payload(sayad_id), service="sayad_cheque"
        )
        return helpers.read_sayad_cheque(answer)

    def sayad_cheque_chain(
        self,
        sayad_id: str,
        national_code: str,
        *,
        cheque_type: str = CHEQUE_TYPE_SAYADI,
    ) -> SayadChequeChain:
        """A cheque's transfer chain (استعلام زنجیره انتقالات چک صیادی).

        ``national_code`` is the **issuer's**, not the current holder's.
        """
        answer = self._inquiry(
            paths.SAYAD_CHEQUE_CHAIN,
            helpers.sayad_chain_payload(sayad_id, national_code, cheque_type),
            service="sayad_cheque_chain",
        )
        return helpers.read_sayad_chain(answer)

    def bounced_cheque(
        self,
        national_code: str,
        *,
        nationality_type: int = NATIONALITY_IRANIAN,
    ) -> BouncedCheque:
        """How many returned cheques stand against a person (استعلام چک برگشتی).

        A count of zero is a successful inquiry; the record is falsy in that case.
        """
        answer = self._inquiry(
            paths.BOUNCED_CHEQUE,
            helpers.bounced_cheque_payload(national_code, nationality_type),
            service="bounced_cheque",
        )
        return helpers.read_bounced_cheque(answer)
