"""Utility services (خدماتی) — companies, addresses, vehicles, Enamad, OCR and bills.

Seventeen inquiries, in the same five-file layout every family uses. Named ``utility`` rather than
``services`` — which is what Zohal's own tag «خدماتی» translates to — so that it does not collide
with the :mod:`zohal_sdk.services` package holding all five families.
"""

from zohal_sdk.services.utility.async_engine import UtilityAsyncMixin as UtilityAsyncMixin
from zohal_sdk.services.utility.data import BillTerm as BillTerm
from zohal_sdk.services.utility.data import BoardMember as BoardMember
from zohal_sdk.services.utility.data import BoardMembers as BoardMembers
from zohal_sdk.services.utility.data import Company as Company
from zohal_sdk.services.utility.data import Enamad as Enamad
from zohal_sdk.services.utility.data import Finglish as Finglish
from zohal_sdk.services.utility.data import GasBill as GasBill
from zohal_sdk.services.utility.data import MobileBill as MobileBill
from zohal_sdk.services.utility.data import NationalCardFront as NationalCardFront
from zohal_sdk.services.utility.data import NationalCardOcr as NationalCardOcr
from zohal_sdk.services.utility.data import PostalAddress as PostalAddress
from zohal_sdk.services.utility.data import UtilityBill as UtilityBill
from zohal_sdk.services.utility.data import VehicleViolation as VehicleViolation
from zohal_sdk.services.utility.data import VehicleViolations as VehicleViolations
from zohal_sdk.services.utility.data import (
    VehicleViolationsSummary as VehicleViolationsSummary,
)
from zohal_sdk.services.utility.data import VoiceOtp as VoiceOtp
from zohal_sdk.services.utility.sync_engine import UtilitySyncMixin as UtilitySyncMixin
