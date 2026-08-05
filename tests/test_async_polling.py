"""The async polling helpers, which are where a blocking sleep would do real damage.

A ``time.sleep`` inside these loops would park the whole event loop for the length of the wait —
minutes, on a credit report — stalling every other request in the process rather than just the one
waiting. So these tests assert not only that the loops terminate correctly, but that they yield:
the last one runs several waits concurrently and fails if they were serialised.
"""

import asyncio
import time
from collections.abc import Callable
from typing import Any

import pytest

from tests.conftest import FakeTransport, envelope
from zohal_sdk import ZohalAsync
from zohal_sdk.common.exceptions import ZohalPollTimeoutError

Example = Callable[..., dict[str, Any]]

SESSION_ID = "0f3a5c1e-1111-2222-3333-444455556666"
REFERENCE_ID = "69061561dXXXXXXXX10fb63e"


def liveness(status: str, result: str | None = None) -> dict[str, Any]:
    return {
        "result": 1,
        "response_body": {"status": status, "result": result, "type": "liveness"},
    }


class TestBiometricPolling:
    async def test_it_returns_once_the_session_is_final(
        self, async_client: ZohalAsync, transport: FakeTransport
    ) -> None:
        transport.reply(liveness("pending"))
        transport.reply(liveness("pending"))
        transport.reply(liveness("completed", "matched"))
        record = await async_client.wait_for_biometric_result(SESSION_ID, timeout=60, interval=3)
        assert record.matched
        assert len(transport.calls) == 3
        assert transport.slept == [3, 3]

    async def test_it_raises_once_the_budget_is_spent(
        self,
        async_client: ZohalAsync,
        transport: FakeTransport,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        ticks = iter([0.0, 10.0, 20.0])
        monkeypatch.setattr(type(async_client), "_now", staticmethod(lambda: next(ticks)))
        transport.reply(liveness("pending"))
        with pytest.raises(ZohalPollTimeoutError) as caught:
            await async_client.wait_for_biometric_result(SESSION_ID, timeout=5, interval=10)
        assert caught.value.last_status == "pending"


class TestCreditPolling:
    async def test_it_returns_once_the_report_completes(
        self, async_client: ZohalAsync, transport: FakeTransport, example: Example
    ) -> None:
        transport.reply(envelope({"status": "pending"}))
        transport.reply(example("/services/inquiry/credit_inquiry/result/{reference_id}"))
        report = await async_client.wait_for_credit_result(REFERENCE_ID, timeout=60, interval=5)
        assert report.is_completed
        assert transport.slept == [5]

    async def test_it_raises_once_the_budget_is_spent(
        self,
        async_client: ZohalAsync,
        transport: FakeTransport,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        ticks = iter([0.0, 100.0, 200.0])
        monkeypatch.setattr(type(async_client), "_now", staticmethod(lambda: next(ticks)))
        transport.reply(envelope({"status": "pending"}))
        with pytest.raises(ZohalPollTimeoutError):
            await async_client.wait_for_credit_result(REFERENCE_ID, timeout=60)


class TestTheLoopIsNotBlocked:
    async def test_concurrent_waits_overlap_rather_than_serialising(
        self, async_client: ZohalAsync, transport: FakeTransport, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Restore a real (tiny) sleep: the point is whether it yields, not how long it takes.
        async def real_sleep(self: Any, seconds: float) -> None:
            transport.slept.append(seconds)
            await asyncio.sleep(0.05)

        monkeypatch.setattr(type(async_client), "_sleep", real_sleep)

        # Eight pending replies before the completion, so that all four waiters are guaranteed two
        # sleeps each: the queue is shared, and with fewer replies the later waiters would reach
        # the completion without ever sleeping — which would make this assertion vacuous.
        waiters, sleeps_each = 4, 2
        for _ in range(waiters * sleeps_each):
            transport.reply(liveness("pending"))
        transport.reply(liveness("completed", "matched"))

        started = time.monotonic()
        results = await asyncio.gather(
            *(
                async_client.wait_for_biometric_result(SESSION_ID, timeout=10, interval=1)
                for _ in range(waiters)
            )
        )
        elapsed = time.monotonic() - started

        assert all(r.matched for r in results)
        assert len(transport.slept) == waiters * sleeps_each
        # Eight sleeps of 0.05s. Overlapped, the four waiters finish in about two sleeps (~0.10s);
        # a blocking sleep would serialise all eight into ~0.40s.
        assert elapsed < 0.25, f"the waits serialised ({elapsed:.3f}s) — the loop blocked"
