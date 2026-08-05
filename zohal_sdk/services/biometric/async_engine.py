"""Video identity verification (احراز هویت ویدیویی), async engine."""

from zohal_sdk.common.engine import AsyncEngine, next_poll_delay
from zohal_sdk.common.exceptions import ZohalPollTimeoutError
from zohal_sdk.common.http import FileInput
from zohal_sdk.services.biometric import constants as paths
from zohal_sdk.services.biometric import helpers
from zohal_sdk.services.biometric.constants import (
    DEFAULT_POLL_INTERVAL,
    DEFAULT_POLL_TIMEOUT,
    MEDIA_SELFIE_VIDEO,
)
from zohal_sdk.services.biometric.data import (
    BiometricMedia,
    BiometricResult,
    BiometricSession,
)


class BiometricAsyncMixin(AsyncEngine):
    """Video identity verification, on the async engine.

    Three calls in sequence: upload the video, open a session against it, then collect the result
    — either from your callback URL, or by polling. Composed into
    :class:`~zohal_sdk.ZohalAsync`.
    """

    async def upload_biometric_media(
        self, file: FileInput, media_type: str = MEDIA_SELFIE_VIDEO
    ) -> BiometricMedia:
        """Upload a selfie video and get back the UUID a session is opened against.

        ``file`` is a path, raw ``bytes``, or an open binary file.
        """
        answer = await self._session_upload(
            paths.MEDIA_UPLOAD,
            files={"file": file},
            fields=helpers.media_fields(media_type),
            service="upload_biometric_media",
        )
        return helpers.read_media(answer)

    async def start_liveness(
        self,
        national_code: str,
        birth_date: str,
        national_card_serial: str,
        selfie_video_id: str,
        *,
        callback_url: str | None = None,
    ) -> BiometricSession:
        """Open a liveness check against an uploaded video (ثبت درخواست بررسی Liveness).

        ``selfie_video_id`` is the ``id`` from :meth:`upload_biometric_media`. Supply
        ``callback_url`` and Zohal posts the finished result there, which is what a web
        application should do rather than hold a request open on
        :meth:`wait_for_biometric_result`.
        """
        answer = await self._session(
            paths.LIVENESS_SESSION,
            helpers.liveness_payload(
                national_code, birth_date, national_card_serial, selfie_video_id, callback_url
            ),
            service="start_liveness",
        )
        return helpers.read_session(answer)

    async def biometric_result(self, session_id: str) -> BiometricResult:
        """A liveness session's current state (دریافت نتیجه).

        Returns whatever Zohal has now, which is often ``status="pending"`` — that is a successful
        inquiry, not a failure, and the record is falsy until it has both completed and matched.
        """
        answer = await self._session_get(
            helpers.result_path(session_id), service="biometric_result"
        )
        return helpers.read_result(answer, session_id)

    async def wait_for_biometric_result(
        self,
        session_id: str,
        *,
        timeout: float = DEFAULT_POLL_TIMEOUT,
        interval: float = DEFAULT_POLL_INTERVAL,
    ) -> BiometricResult:
        """Poll until the session reaches a state that will not change again.

        Raises :class:`~zohal_sdk.common.exceptions.ZohalPollTimeoutError` if ``timeout`` seconds
        pass first — which does not cancel anything at Zohal's end, so the same ``session_id`` can
        be polled again or picked up from the callback.

        Prefer ``callback_url`` on :meth:`start_liveness` where you can — polling blocks the
        caller for as long as the video takes to process.
        """
        started = self._now()
        while True:
            result = await self.biometric_result(session_id)
            if result.is_final:
                return result
            delay = next_poll_delay(interval, started, self._now(), timeout)
            if delay is None:
                raise ZohalPollTimeoutError(
                    f"liveness session {session_id} was still {result.status!r} after {timeout}s",
                    reference=session_id,
                    last_status=result.status,
                )
            await self._sleep(delay)
