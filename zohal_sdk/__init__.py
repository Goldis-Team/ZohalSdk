"""A typed SDK for Zohal's inquiry web services, in a sync and an async flavour.

All 37 endpoints — banking, identity, company and utility, video biometrics, and credit scoring —
on one client. :class:`ZohalSync` and :class:`ZohalAsync` carry the same methods with the same
arguments and the same return types; moving a call site between them is adding or removing
``await``.

    from zohal_sdk import ZohalSync

    zohal = ZohalSync(token="…")

    card = zohal.card_to_iban("6362141112345674")
    print(card.iban, card.bank_name, card.name)

    if zohal.shahkar(national_code="0021234567", mobile="09121234567"):
        person = zohal.national_identity("0021234567", "1377/07/19")
        print(person.first_name, person.last_name)

Every inquiry is billed per call, so arguments are normalised and checked before the request goes
out — Persian digits are folded to ASCII, and a national code, IBAN or card number whose own
checksum does not hold raises :class:`ZohalValidationError` locally rather than being paid for.

Zohal answers only requests from IPs registered on your panel; an otherwise-inexplicable
:class:`ZohalAuthenticationError` usually means that, not the token.

The code behind the flat client is split per service family under :mod:`zohal_sdk.services`, each
in the same five-file layout: ``constants.py``, ``data.py`` (dataclasses only), ``helpers.py`` (the
pure payload-building and response-reading), and ``sync_engine.py`` / ``async_engine.py``.
"""

from zohal_sdk.client import ZohalAsync as ZohalAsync
from zohal_sdk.client import ZohalSync as ZohalSync
from zohal_sdk.common.constants import BASE_URL as BASE_URL
from zohal_sdk.common.constants import DEFAULT_TIMEOUT as DEFAULT_TIMEOUT
from zohal_sdk.common.constants import RESULT_MEANINGS as RESULT_MEANINGS
from zohal_sdk.common.constants import RESULT_SUCCESS as RESULT_SUCCESS
from zohal_sdk.common.data import InquiryRecord as InquiryRecord
from zohal_sdk.common.data import MatchResult as MatchResult
from zohal_sdk.common.data import ZohalConfig as ZohalConfig
from zohal_sdk.common.exceptions import ZohalAuthenticationError as ZohalAuthenticationError
from zohal_sdk.common.exceptions import ZohalConfigurationError as ZohalConfigurationError
from zohal_sdk.common.exceptions import ZohalError as ZohalError
from zohal_sdk.common.exceptions import ZohalNetworkError as ZohalNetworkError
from zohal_sdk.common.exceptions import ZohalPollTimeoutError as ZohalPollTimeoutError
from zohal_sdk.common.exceptions import ZohalServiceError as ZohalServiceError
from zohal_sdk.common.exceptions import ZohalValidationError as ZohalValidationError
from zohal_sdk.common.http import FileInput as FileInput
from zohal_sdk.services.banking import AccountToIban as AccountToIban
from zohal_sdk.services.banking import BouncedCheque as BouncedCheque
from zohal_sdk.services.banking import CardHolder as CardHolder
from zohal_sdk.services.banking import CardNameMatch as CardNameMatch
from zohal_sdk.services.banking import CardToAccount as CardToAccount
from zohal_sdk.services.banking import CardToIban as CardToIban
from zohal_sdk.services.banking import IbanInfo as IbanInfo
from zohal_sdk.services.banking import SayadCheque as SayadCheque
from zohal_sdk.services.banking import SayadChequeChain as SayadChequeChain
from zohal_sdk.services.banking import SayadChequeCustomer as SayadChequeCustomer
from zohal_sdk.services.banking import SayadChequeLink as SayadChequeLink
from zohal_sdk.services.biometric import BiometricMedia as BiometricMedia
from zohal_sdk.services.biometric import BiometricResult as BiometricResult
from zohal_sdk.services.biometric import BiometricSession as BiometricSession
from zohal_sdk.services.credit import BouncedChequeSection as BouncedChequeSection
from zohal_sdk.services.credit import ChequeStatusCount as ChequeStatusCount
from zohal_sdk.services.credit import ContractSummary as ContractSummary
from zohal_sdk.services.credit import CreditContract as CreditContract
from zohal_sdk.services.credit import CreditOtpRequest as CreditOtpRequest
from zohal_sdk.services.credit import CreditOtpVerification as CreditOtpVerification
from zohal_sdk.services.credit import CreditReport as CreditReport
from zohal_sdk.services.credit import CreditScore as CreditScore
from zohal_sdk.services.credit import InquiryHistory as InquiryHistory
from zohal_sdk.services.credit import InquiryStats as InquiryStats
from zohal_sdk.services.credit import JudiciaryData as JudiciaryData
from zohal_sdk.services.credit import JudiciarySection as JudiciarySection
from zohal_sdk.services.credit import NegativeStatus as NegativeStatus
from zohal_sdk.services.credit import PersonalInformation as PersonalInformation
from zohal_sdk.services.credit import PersonRole as PersonRole
from zohal_sdk.services.credit import PichakData as PichakData
from zohal_sdk.services.credit import PichakSection as PichakSection
from zohal_sdk.services.credit import Repayment as Repayment
from zohal_sdk.services.credit import ReportSection as ReportSection
from zohal_sdk.services.credit import ScoreCode as ScoreCode
from zohal_sdk.services.credit import TaxSection as TaxSection
from zohal_sdk.services.credit import TaxYear as TaxYear
from zohal_sdk.services.identity import NationalIdentity as NationalIdentity
from zohal_sdk.services.utility import BillTerm as BillTerm
from zohal_sdk.services.utility import BoardMember as BoardMember
from zohal_sdk.services.utility import BoardMembers as BoardMembers
from zohal_sdk.services.utility import Company as Company
from zohal_sdk.services.utility import Enamad as Enamad
from zohal_sdk.services.utility import Finglish as Finglish
from zohal_sdk.services.utility import GasBill as GasBill
from zohal_sdk.services.utility import MobileBill as MobileBill
from zohal_sdk.services.utility import NationalCardFront as NationalCardFront
from zohal_sdk.services.utility import NationalCardOcr as NationalCardOcr
from zohal_sdk.services.utility import PostalAddress as PostalAddress
from zohal_sdk.services.utility import UtilityBill as UtilityBill
from zohal_sdk.services.utility import VehicleViolation as VehicleViolation
from zohal_sdk.services.utility import VehicleViolations as VehicleViolations
from zohal_sdk.services.utility import VehicleViolationsSummary as VehicleViolationsSummary
from zohal_sdk.services.utility import VoiceOtp as VoiceOtp

__version__ = "0.1.0"
