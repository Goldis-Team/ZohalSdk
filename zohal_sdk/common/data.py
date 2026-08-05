"""Value objects shared by every service family, in both engines.

Dataclasses only. Endpoints and fixed values live in ``constants.py``; the functions that build
payloads and read responses live in each family's ``helpers.py``.
"""

from dataclasses import dataclass, field
from typing import Any

from zohal_sdk.common.constants import BASE_URL, DEFAULT_TIMEOUT


@dataclass(frozen=True)
class ZohalConfig:
    """How to reach Zohal, and as whom.

    ``token`` is the API token from **توسعه‌دهندگان → توکن** on your panel. It is sent as
    ``Authorization: Bearer <token>``. Zohal also refuses requests from addresses you have not
    registered, so a correct token is necessary but not sufficient.
    """

    token: str

    base_url: str = BASE_URL
    """Overridable for a staging host or a local recording proxy; Zohal publishes only one."""

    timeout: float = DEFAULT_TIMEOUT
    """Seconds per request."""


@dataclass(frozen=True)
class InquiryRecord:
    """Base for every record this SDK returns.

    Each endpoint's own record subclasses this and adds exactly the fields *that* endpoint
    documents, typed, so reading an answer never means digging through ``raw``. What is here is
    what every answer carries.

    Fields default to ``None`` rather than being required: Zohal omits fields it has nothing to
    say about, and a record is descriptive — nothing in this SDK decides anything on one — so a
    missing field is reported as missing rather than raising. The values that *would* be worth
    failing on are the inputs, and those are checked before the call in
    :mod:`zohal_sdk.common.utils`.
    """

    message: str | None = None
    """Zohal's own message for this answer, normally the Persian ``"موفق"`` on success."""

    raw: dict[str, Any] = field(default_factory=dict[str, Any])
    """Zohal's decoded response, untouched, for logging and support tickets."""


@dataclass(frozen=True)
class MatchResult(InquiryRecord):
    """The answer to a yes/no inquiry — Shahkar, and the card/IBAN-against-identity checks.

    A ``False`` here is a successful inquiry with a negative answer, not a failure: the call
    reached Zohal, was billed, and reported that the two things do not belong to the same person.
    Failures raise :class:`~zohal_sdk.common.exceptions.ZohalServiceError` instead.

    Falsy when unmatched, so ``if not client.shahkar(...):`` reads the way it should.
    """

    matched: bool = False
    """Whether Zohal reported the two values as belonging together."""

    def __bool__(self) -> bool:
        return self.matched
