"""The two clients: every Zohal endpoint, on one object, in a sync and an async flavour.

Zohal is one provider behind one token, so there is one client rather than five — every endpoint is
a direct method on it. The code behind them is still split per service family under
:mod:`zohal_sdk.services`; each family contributes a mixin, and these two classes compose all five.

Both carry exactly the same methods with the same arguments and the same return types; the only
difference is the ``async``. Porting a call site from one engine to the other is adding or removing
``await``, never a rewrite — which is the whole point of shipping both.
"""

from zohal_sdk.common.engine import AsyncEngine, SyncEngine
from zohal_sdk.services import (
    BankingAsyncMixin,
    BankingSyncMixin,
    BiometricAsyncMixin,
    BiometricSyncMixin,
    CreditAsyncMixin,
    CreditSyncMixin,
    IdentityAsyncMixin,
    IdentitySyncMixin,
    UtilityAsyncMixin,
    UtilitySyncMixin,
)


class ZohalSync(
    BankingSyncMixin,
    IdentitySyncMixin,
    UtilitySyncMixin,
    BiometricSyncMixin,
    CreditSyncMixin,
    SyncEngine,
):
    """Every Zohal endpoint, on the sync engine — for scripts, Django, and Celery workers.

        from zohal_sdk import ZohalSync

        zohal = ZohalSync(token="…")
        print(zohal.card_to_iban("6362141112345674").iban)
        if zohal.shahkar(national_code="0021234567", mobile="09121234567"):
            ...

    Build one client per token rather than caching one globally, and pass the token in — the SDK
    never reads it from the environment.

    Every inquiry is billed, so arguments are checked locally first: a national code whose checksum
    does not hold raises :class:`~zohal_sdk.common.exceptions.ZohalValidationError` before any call
    is made. A rejection from Zohal raises
    :class:`~zohal_sdk.common.exceptions.ZohalServiceError`. A *negative answer* — an unmatched
    Shahkar, a person with returned cheques — is a successful inquiry and comes back as a record.
    """


class ZohalAsync(
    BankingAsyncMixin,
    IdentityAsyncMixin,
    UtilityAsyncMixin,
    BiometricAsyncMixin,
    CreditAsyncMixin,
    AsyncEngine,
):
    """Every Zohal endpoint, on the async engine — for FastAPI, aiohttp, anything on asyncio.

    The same calls as :class:`ZohalSync`, awaited:

        from zohal_sdk import ZohalAsync

        zohal = ZohalAsync(token="…")
        card = await zohal.card_to_iban("6362141112345674")

    Concurrency is real — these overlap rather than queueing, which matters when a single vehicle
    or company inquiry can take seconds at the government end:

        import asyncio

        cards = await asyncio.gather(*(zohal.card_to_iban(n) for n in numbers))
    """
