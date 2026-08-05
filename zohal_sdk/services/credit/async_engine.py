"""Credit scoring (استعلام اعتبارسنجی), async engine."""

from zohal_sdk.common.engine import AsyncEngine, next_poll_delay
from zohal_sdk.common.exceptions import ZohalPollTimeoutError
from zohal_sdk.services.credit import constants as paths
from zohal_sdk.services.credit import helpers
from zohal_sdk.services.credit.constants import DEFAULT_POLL_INTERVAL, DEFAULT_POLL_TIMEOUT
from zohal_sdk.services.credit.data import (
    CreditOtpRequest,
    CreditOtpVerification,
    CreditReport,
)


class CreditAsyncMixin(AsyncEngine):
    """Credit scoring, on the async engine.

    Three steps: send the person an OTP, submit what they typed, then collect the report against
    the same ``reference_id``. The OTP is the person consenting to their own credit file being
    pulled — which is why this flow has one at all, and why the reference must be carried through
    rather than regenerated. Composed into :class:`~zohal_sdk.ZohalAsync`.
    """

    async def credit_send_otp(self, national_code: str, mobile: str) -> CreditOtpRequest:
        """Send the consent OTP (ارسال OTP).

        Keep the returned ``reference_id``: both remaining steps are scoped to it.
        """
        raw = await self._bare(
            paths.SEND_OTP,
            helpers.send_otp_payload(national_code, mobile),
            service="credit_send_otp",
        )
        return helpers.read_otp_request(raw)

    async def credit_verify_otp(self, reference_id: str, otp: str) -> CreditOtpVerification:
        """Submit the code the person received (اعتبارسنجی OTP).

        Zohal publishes no response body here, so a call that did not raise is a call that
        succeeded — the report is then collected against the same ``reference_id``.
        """
        raw = await self._bare(
            paths.VERIFY_OTP,
            helpers.verify_otp_payload(reference_id, otp),
            service="credit_verify_otp",
        )
        return helpers.read_otp_verification(raw, reference_id)

    async def credit_result(self, reference_id: str) -> CreditReport:
        """The report as it stands (دریافت نتیجه).

        Often ``status="pending"`` for the first while, which is a successful inquiry with an
        unfinished report — the record is falsy until it completes.
        """
        answer = await self._inquiry_get(helpers.result_path(reference_id), service="credit_result")
        return helpers.read_report(answer, reference_id)

    async def wait_for_credit_result(
        self,
        reference_id: str,
        *,
        timeout: float = DEFAULT_POLL_TIMEOUT,
        interval: float = DEFAULT_POLL_INTERVAL,
    ) -> CreditReport:
        """Poll until the report reaches a state that will not change again.

        Raises :class:`~zohal_sdk.common.exceptions.ZohalPollTimeoutError` if ``timeout`` seconds
        pass first, which cancels nothing at Zohal's end — the same ``reference_id`` can be polled
        again afterwards.

        A full report is assembled from a dozen upstream systems, so this blocks the caller for
        minutes. Prefer running it out of a worker rather than a request handler.
        """
        started = self._now()
        while True:
            report = await self.credit_result(reference_id)
            if report.is_final:
                return report
            delay = next_poll_delay(interval, started, self._now(), timeout)
            if delay is None:
                raise ZohalPollTimeoutError(
                    f"credit report {reference_id} was still {report.status!r} after {timeout}s",
                    reference=reference_id,
                    last_status=report.status,
                )
            await self._sleep(delay)
