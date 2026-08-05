"""One error hierarchy across every service family.

Everything here is raised, including a service-level rejection. Zohal's endpoints are *inquiries* —
asking again is always safe, and no state at Zohal depends on the answer — so there is no reason to
soften a failure into a return value the way a payment verification must. What is not an error is a
*negative answer*: a Shahkar call that reports ``matched=False`` succeeded, and comes back as a
record whose ``matched`` is ``False``.

:class:`ZohalValidationError` is the one raised before any network call. Every Zohal endpoint is
billed per request, so an input that cannot possibly be right is refused locally rather than paid
for.
"""

from typing import Any


class ZohalError(Exception):
    """Base for everything this SDK raises."""


class ZohalConfigurationError(ZohalError):
    """The client cannot be addressed as configured — no token, or a nonsensical timeout.

    Raised at construction, before any network call, so a half-configured client fails while you
    are wiring it up rather than on the first inquiry.
    """


class ZohalValidationError(ZohalError):
    """An argument could not be what the service needs, and the call was not made.

    Every inquiry is billed, so a national code whose checksum does not hold, an IBAN that fails
    mod-97, or a Jalali date with a 31st of Esfand in it is refused here — Zohal would charge for
    the round trip and answer ``result=6``.

    ``field`` is the argument at fault, and ``value`` is what was passed after normalisation.
    """

    def __init__(self, message: str, *, field: str, value: Any = None) -> None:
        super().__init__(message)
        self.field = field
        """The name of the argument that was rejected."""
        self.value = value
        """What it held, after digit folding and separator stripping."""


class ZohalNetworkError(ZohalError):
    """Zohal could not be reached, timed out, or answered with something undecodable."""


class ZohalAuthenticationError(ZohalError):
    """Zohal rejected the token, or the request did not come from an address it knows.

    Zohal answers only requests originating from IPs registered on your panel, and an unregistered
    address is refused the same way a bad token is. If the token is right, that is usually what
    this means — check **توسعه‌دهندگان → IPها** before re-issuing anything.
    """

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status
        """The HTTP status Zohal answered with, 401 or 403."""


class ZohalServiceError(ZohalError):
    """Zohal was reached and declined the inquiry.

    Carries Zohal's own ``result`` code, the ``error_code`` string where it sent one, its message
    — usually Persian, and usually the most useful thing in here — and the decoded body untouched.
    """

    def __init__(
        self,
        message: str,
        *,
        result: int | None = None,
        error_code: str | None = None,
        status: int | None = None,
        raw: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.result = result
        """Zohal's ``result`` code: 4 invalid request, 5 internal error, 6 bad input."""
        self.error_code = error_code
        """Zohal's ``error_code``, e.g. ``"NATIONAL_ID_INVALID"`` — ``None`` where it sent none."""
        self.status = status
        """The HTTP status, which on its own decides nothing: these bodies arrive under 400, 404,
        500 and 503 as readily as under 200."""
        self.raw = raw or {}
        """Zohal's decoded response, untouched, for logging and support tickets."""


class ZohalPollTimeoutError(ZohalError):
    """A ``wait_for_*`` helper ran out of time before the session reached a terminal state.

    The work is not cancelled by this — Zohal is still processing, and the same reference can be
    polled again or picked up from the callback. ``last_status`` is where it had got to.
    """

    def __init__(self, message: str, *, reference: str, last_status: str | None = None) -> None:
        super().__init__(message)
        self.reference = reference
        """The session id or reference id being polled."""
        self.last_status = last_status
        """The last status seen before the budget ran out, e.g. ``"pending"``."""
