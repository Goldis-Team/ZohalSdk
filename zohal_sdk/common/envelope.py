"""Reading Zohal's answer, in the three shapes it comes in.

Every response carries a top-level ``result`` — ``1`` for success, ``4``/``5``/``6`` for the ways it
can fail. What sits under it is not quite as uniform:

1. **The inquiry envelope**, on all 34 endpoints under ``/services/inquiry/`` except the two credit
   OTP steps — ``{"result": 1, "response_body": {"data": {…}, "error_code": null,
   "message": "موفق"}}``. :func:`read_data` returns the ``data`` object.

2. **The bare body**, on the three biometric endpoints: ``response_body`` *is* the payload, with no
   ``data`` wrapper and no ``message`` —  ``{"result": 1, "response_body": {"session_id": …,
   "status": "pending"}}``. :func:`read_body` returns ``response_body`` itself.

3. **No envelope at all**, on the two credit OTP steps, which answer ``{"reference_id": …,
   "status": "pending"}`` at the top level with no ``result`` to check. :func:`read_bare` takes the
   whole body and has nothing to verify but the transport's own status.

**The HTTP status decides nothing here.** Zohal documents ``result=6`` under 503 for a service that
is down, ``result=5`` under 500 for a fault of its own, ``result=6`` under 404 for a service that
does not exist, and ``result=6`` under 400 with an ``error_code`` such as ``NATIONAL_ID_INVALID`` —
all in this same envelope. The body is what says what happened; the status is passed through onto
the exception for the support ticket. The one exception is 401/403, which
:mod:`zohal_sdk.common.http` turns into
:class:`~zohal_sdk.common.exceptions.ZohalAuthenticationError` before this module sees it.
"""

from typing import Any

from zohal_sdk.common.constants import RESULT_MEANINGS, RESULT_MEANINGS_EN, RESULT_SUCCESS
from zohal_sdk.common.exceptions import ZohalServiceError
from zohal_sdk.common.utils import as_dict, as_int, as_text


def _fail(raw: dict[str, Any], status: int, service: str) -> ZohalServiceError:
    """Build the exception for a rejected inquiry, saying as much as the body allows.

    Zohal's own Persian ``message`` is preferred over anything this SDK could compose — it is
    written for the person who has to fix the input, and it names the field. The ``result`` code's
    English meaning is appended only when there is no message to lead with.
    """
    body = as_dict(raw.get("response_body"))
    result = as_int(raw.get("result"))
    message = as_text(body.get("message")) or as_text(raw.get("message"))
    error_code = as_text(body.get("error_code")) or as_text(body.get("error"))
    meaning = RESULT_MEANINGS_EN.get(result or 0, "unknown result")
    detail = message or RESULT_MEANINGS.get(result or 0) or "no message"
    label = f" [{error_code}]" if error_code else ""
    return ZohalServiceError(
        f"zohal declined {service}: {detail}{label} (result={result}, {meaning})",
        result=result,
        error_code=error_code,
        status=status,
        raw=raw,
    )


def check_result(raw: dict[str, Any], *, status: int, service: str) -> None:
    """Raise unless ``result`` is 1. Every envelope shape that has a ``result`` starts here."""
    if as_int(raw.get("result")) != RESULT_SUCCESS:
        raise _fail(raw, status, service)


def read_data(raw: dict[str, Any], *, status: int, service: str) -> dict[str, Any]:
    """Shape 1 — the inquiry envelope. Returns ``response_body.data``.

    An empty ``data`` on a successful result is returned as an empty dict rather than raising: a
    handful of these endpoints answer with nothing but a message, and the record's fields are all
    optional anyway.
    """
    check_result(raw, status=status, service=service)
    return as_dict(as_dict(raw.get("response_body")).get("data"))


def read_body(raw: dict[str, Any], *, status: int, service: str) -> dict[str, Any]:
    """Shape 2 — the biometric endpoints. Returns ``response_body`` itself."""
    check_result(raw, status=status, service=service)
    return as_dict(raw.get("response_body"))


def read_lenient(raw: dict[str, Any], *, status: int, service: str) -> dict[str, Any]:
    """For the one endpoint whose response Zohal documents not at all — the voice OTP.

    It sits under ``/services/inquiry/`` and so almost certainly answers in shape 1, but "almost
    certainly" is not something to raise on: if the body carries a ``result`` it is checked like
    any other, and if it does not, the HTTP status is used instead. Either way a failure is still
    reported; what is avoided is inventing a failure out of a field Zohal never promised to send.
    """
    if "result" in raw:
        check_result(raw, status=status, service=service)
        body = as_dict(raw.get("response_body"))
        return as_dict(body.get("data")) or body
    if not 200 <= status < 300:
        raise _fail(raw, status, service)
    return raw


def read_bare(raw: dict[str, Any], *, status: int, service: str) -> dict[str, Any]:
    """Shape 3 — the credit OTP steps, which send no ``result`` to check.

    With no ``result`` field there is nothing in the body that reports failure, so the HTTP status
    is all there is: anything outside 2xx is a rejection. This is the only place in the SDK where
    the status decides, and it is because Zohal left nothing else to decide on.
    """
    if not 200 <= status < 300:
        raise _fail(raw, status, service)
    return raw
