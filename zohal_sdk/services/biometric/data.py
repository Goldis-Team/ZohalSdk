"""Video identity verification (احراز هویت ویدیویی) — the records these endpoints return.

Dataclasses only. These three answer in the *bare body* envelope — ``response_body`` is the payload
itself, with no ``data`` wrapper and no ``message`` — so
:attr:`~zohal_sdk.common.data.InquiryRecord.message` is ``None`` on all of them.
"""

from dataclasses import dataclass

from zohal_sdk.common.data import InquiryRecord
from zohal_sdk.services.biometric.constants import (
    RESULT_MATCHED,
    STATUS_COMPLETED,
    TERMINAL_STATUSES,
)


@dataclass(frozen=True)
class BiometricMedia(InquiryRecord):
    """An uploaded video or image (آپلود مدیا بایومتریک)."""

    id: str | None = None
    """The media's UUID. This is what a liveness session is opened against."""

    type: str | None = None
    """Echoed back, e.g. ``"selfie_video"``."""


@dataclass(frozen=True)
class BiometricSession(InquiryRecord):
    """A liveness check that has been accepted for processing (ثبت درخواست بررسی Liveness)."""

    session_id: str | None = None
    """Poll this, or wait for it on your callback URL."""

    status: str | None = None
    """``"pending"`` when the session opens."""


@dataclass(frozen=True)
class BiometricResult(InquiryRecord):
    """How a liveness check turned out (دریافت نتیجه).

    Falsy until the session has both completed *and* matched, so ``if result:`` is a safe gate —
    a session still pending never reads as a pass.
    """

    session_id: str | None = None

    status: str | None = None
    """``"pending"`` while Zohal is still working, ``"completed"`` once it is done."""

    result: str | None = None
    """The verdict on a completed session, e.g. ``"matched"``."""

    reason: str | None = None
    """Why — ``"ACCEPT"`` on a pass, and the rejection code otherwise."""

    type: str | None = None
    """The kind of session, e.g. ``"liveness"``."""

    completed_at: str | None = None

    @property
    def is_final(self) -> bool:
        """Whether this status will not change again — what the polling helpers wait on."""
        return self.status is not None and self.status.lower() in TERMINAL_STATUSES

    @property
    def matched(self) -> bool:
        """Whether the face matched. ``False`` while the session is still pending."""
        return (self.status or "").lower() == STATUS_COMPLETED and (
            self.result or ""
        ).lower() == RESULT_MATCHED

    def __bool__(self) -> bool:
        return self.matched
