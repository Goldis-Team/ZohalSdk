"""Credit scoring (استعلام اعتبارسنجی) — paths and the fixed values this flow defines."""

SEND_OTP = "/services/inquiry/credit_inquiry/send_otp"
VERIFY_OTP = "/services/inquiry/credit_inquiry/verify_otp"
RESULT = "/services/inquiry/credit_inquiry/result/{reference_id}"

STATUS_PENDING = "pending"
STATUS_COMPLETED = "completed"

TERMINAL_STATUSES = frozenset({STATUS_COMPLETED, "failed", "rejected", "error", "expired"})
"""Report states that will not change again, so a poller can stop.

``completed`` is the one Zohal documents; the rest are the shapes a failed report plausibly takes,
treated as terminal so a report that has already gone wrong is not polled until the timeout. A
state Zohal adds later reads as non-terminal, which costs a wait rather than a wrong answer.
"""

SECTION_OK = 200
"""The per-section ``status`` meaning that sub-source answered.

The report is assembled from several government systems, and each reports its own status inside
its own section. ``404`` means that system had nothing on this person — the Central Bank's
bounced-cheque registry answers 404 for someone with no returned cheques — which is an *answer*,
not an error, and is why the SDK does not raise on it.
"""

DEFAULT_POLL_INTERVAL = 5.0
DEFAULT_POLL_TIMEOUT = 300.0
"""Seconds. A full credit report is assembled from a dozen upstream systems and is not quick."""
