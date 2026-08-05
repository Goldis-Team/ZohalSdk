"""Constants shared by every service family and both engines.

Values that are facts about a *specific* family — its paths, the fixed values its own protocol
defines — live in that family's own ``constants.py``. Only what genuinely applies everywhere
belongs here.
"""

BASE_URL = "https://service.zohal.io/api/v0"
"""Zohal's only server. Every path in this SDK is relative to it."""

DEFAULT_TIMEOUT = 30.0
"""Seconds.

Longer than a payment gateway would want, because several of these are not Zohal's own answers:
the vehicle, company and credit inquiries are Zohal relaying a question to a government system
whose own latency it does not control. Short enough that a dead upstream is not a hung worker.
"""

RESULT_SUCCESS = 1
"""The only value of ``result`` that means the inquiry answered."""

RESULT_MEANINGS = {
    1: "درخواست موفق",
    4: "درخواست نامعتبر",
    5: "خطای داخلی سرور زحل",
    6: "ورودی نادرست",
}
"""Zohal's ``result`` codes, as its documentation defines them.

Only ``1`` is success. ``4`` means the request itself was not acceptable, ``5`` is a fault inside
Zohal, and ``6`` covers bad input — which is also what a 404 for an unknown service and a 503 for
a service that is temporarily down both report as.
"""

RESULT_MEANINGS_EN = {
    1: "success",
    4: "invalid request",
    5: "Zohal internal error",
    6: "bad input",
}
"""The same codes in English, for log lines and exception messages."""

AUTH_STATUSES = (401, 403)
"""HTTP statuses that mean the credentials or the caller's IP were rejected.

The only two statuses this SDK decides on before reading the body. Everything else — including
400, 404, 500 and 503 — carries Zohal's normal envelope, and the ``result`` code inside it is what
actually describes the failure.
"""
