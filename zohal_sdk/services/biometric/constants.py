"""Video identity verification (احراز هویت ویدیویی) — paths, media types, session states."""

MEDIA_UPLOAD = "/services/biometric/media/"
LIVENESS_SESSION = "/services/biometric/session/liveness/"
SESSION_RESULT = "/services/biometric/session/{session_id}/result"

MEDIA_SELFIE_VIDEO = "selfie_video"
"""The media ``type`` a liveness session consumes, and the only one Zohal documents."""

STATUS_PENDING = "pending"
STATUS_COMPLETED = "completed"

TERMINAL_STATUSES = frozenset({STATUS_COMPLETED, "failed", "rejected", "error", "expired"})
"""Session states that will not change again, so a poller can stop.

``completed`` is the one Zohal documents. The rest are the shapes a failed session plausibly takes,
and are treated as terminal so that a session which has already gone wrong is not polled until the
caller's timeout expires. A state Zohal invents later is simply not terminal, which costs a wait
rather than a wrong answer — the safer way round.
"""

RESULT_MATCHED = "matched"
"""``result`` on a completed session whose face matched the identity it was checked against."""

DEFAULT_POLL_INTERVAL = 3.0
DEFAULT_POLL_TIMEOUT = 180.0
"""Seconds. Liveness checks involve a video being processed, so the wait is minutes, not seconds."""
