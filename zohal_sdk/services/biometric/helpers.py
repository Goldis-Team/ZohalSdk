"""Video identity verification (احراز هویت ویدیویی) — payload building and response reading.

Pure functions, called by both engines — including the arithmetic behind the polling helpers, so
that "have we waited long enough" is decided in one place rather than twice.
"""

from typing import Any

from zohal_sdk.common.engine import Answer
from zohal_sdk.common.utils import (
    as_text,
    check_birth_date,
    check_national_code,
    check_required,
)
from zohal_sdk.services.biometric.constants import MEDIA_SELFIE_VIDEO, SESSION_RESULT
from zohal_sdk.services.biometric.data import (
    BiometricMedia,
    BiometricResult,
    BiometricSession,
)


def media_fields(media_type: str = MEDIA_SELFIE_VIDEO) -> dict[str, str]:
    return {"type": check_required(media_type, field="media_type", label="media type")}


def liveness_payload(
    national_code: str,
    birth_date: str,
    national_card_serial: str,
    selfie_video_id: str,
    callback_url: str | None,
) -> dict[str, Any]:
    """Open a liveness session against an already-uploaded video.

    ``selfie_video_id`` is the UUID from
    :meth:`~zohal_sdk.ZohalSync.upload_biometric_media` — the video is uploaded first and
    referenced here, never sent inline.
    """
    payload: dict[str, Any] = {
        "national_code": check_national_code(national_code),
        "birth_date": check_birth_date(birth_date),
        "national_card_serial": check_required(
            national_card_serial, field="national_card_serial", label="national card serial"
        ),
        "media": {
            MEDIA_SELFIE_VIDEO: check_required(
                selfie_video_id, field="selfie_video_id", label="selfie video id"
            )
        },
    }
    if callback_url:
        # Optional: Zohal posts the finished result here, which is the alternative to polling and
        # the better one for anything running behind a request handler.
        payload["callback_url"] = check_required(
            callback_url, field="callback_url", label="callback URL"
        )
    return payload


def result_path(session_id: str) -> str:
    return SESSION_RESULT.format(
        session_id=check_required(session_id, field="session_id", label="session id")
    )


def read_media(answer: Answer) -> BiometricMedia:
    return BiometricMedia(
        id=as_text(answer.data.get("id")),
        type=as_text(answer.data.get("type")),
        message=answer.message,
        raw=answer.raw,
    )


def read_session(answer: Answer) -> BiometricSession:
    return BiometricSession(
        session_id=as_text(answer.data.get("session_id")),
        status=as_text(answer.data.get("status")),
        message=answer.message,
        raw=answer.raw,
    )


def read_result(answer: Answer, session_id: str) -> BiometricResult:
    data = answer.data
    return BiometricResult(
        # Zohal's result payload does not echo the session id, so it is carried over from the
        # request — a record that cannot say which session it describes is not much of a record.
        session_id=as_text(data.get("session_id")) or session_id,
        status=as_text(data.get("status")),
        result=as_text(data.get("result")),
        reason=as_text(data.get("reason")),
        type=as_text(data.get("type")),
        completed_at=as_text(data.get("completed_at")),
        message=answer.message,
        raw=answer.raw,
    )
