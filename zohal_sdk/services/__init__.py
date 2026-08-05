"""Every service family, one directory each.

Zohal groups its endpoints under five tags, and each becomes a directory here holding the same five
things: ``constants.py`` (paths and the fixed values its endpoints define), ``data.py`` (the records
they return — dataclasses only), ``helpers.py`` (the pure functions that build payloads and read
responses), and ``sync_engine.py`` / ``async_engine.py``, which are thin shells over both. That
split is why the two engines cannot drift apart: every decision about what Zohal said lives in
``helpers.py`` and is shared, so only the transport call differs.

Each engine module exposes a **mixin** rather than a standalone client, because Zohal is one
provider behind one token: :class:`~zohal_sdk.ZohalSync` composes all five so that every endpoint
is a direct method on one object. The per-family split is how the code is organised; the flat
client is how it is used.

| Directory | Zohal's tag | Endpoints |
| --- | --- | --- |
| ``banking`` | بانکی | 10 |
| ``identity`` | احراز هویت | 4 |
| ``utility`` | خدماتی | 17 |
| ``biometric`` | احراز هویت ویدیویی | 3 |
| ``credit`` | استعلام اعتبارسنجی | 3 |
"""

from zohal_sdk.services.banking import BankingAsyncMixin as BankingAsyncMixin
from zohal_sdk.services.banking import BankingSyncMixin as BankingSyncMixin
from zohal_sdk.services.biometric import BiometricAsyncMixin as BiometricAsyncMixin
from zohal_sdk.services.biometric import BiometricSyncMixin as BiometricSyncMixin
from zohal_sdk.services.credit import CreditAsyncMixin as CreditAsyncMixin
from zohal_sdk.services.credit import CreditSyncMixin as CreditSyncMixin
from zohal_sdk.services.identity import IdentityAsyncMixin as IdentityAsyncMixin
from zohal_sdk.services.identity import IdentitySyncMixin as IdentitySyncMixin
from zohal_sdk.services.utility import UtilityAsyncMixin as UtilityAsyncMixin
from zohal_sdk.services.utility import UtilitySyncMixin as UtilitySyncMixin
