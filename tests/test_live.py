"""Live inquiries against the real service. Skipped unless you opt in.

Every call here is **billed to your Zohal account** and only works from an IP registered on your
panel, so the whole module is skipped unless ``ZOHAL_TOKEN`` is set. Run it deliberately:

    ZOHAL_TOKEN=… pytest -m integration

Only the cheapest, least personal endpoints are exercised — an Enamad lookup against a public
domain, and transliteration, which involves nobody's data at all. Inquiries that need a real
person's national code are opt-in on top of that, via ``ZOHAL_TEST_NATIONAL_CODE`` and
``ZOHAL_TEST_MOBILE``, because running them means pulling a real person's records.
"""

import os

import pytest

from zohal_sdk import ZohalAsync, ZohalSync

TOKEN = os.environ.get("ZOHAL_TOKEN", "").strip()
NATIONAL_CODE = os.environ.get("ZOHAL_TEST_NATIONAL_CODE", "").strip()
MOBILE = os.environ.get("ZOHAL_TEST_MOBILE", "").strip()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not TOKEN, reason="ZOHAL_TOKEN is not set; these calls are billed"),
]


@pytest.fixture
def live() -> ZohalSync:
    return ZohalSync(token=TOKEN)


def test_enamad_inquiry_against_a_public_domain(live: ZohalSync) -> None:
    seal = live.enamad_inquiry("digikala.com")
    assert seal.domain
    assert seal.id is not None


def test_persian_to_finglish_involves_nobodys_data(live: ZohalSync) -> None:
    assert live.persian_to_finglish("محمد").finglish_text


async def test_the_async_engine_reaches_the_same_service() -> None:
    seal = await ZohalAsync(token=TOKEN).enamad_inquiry("digikala.com")
    assert seal.domain


@pytest.mark.skipif(
    not (NATIONAL_CODE and MOBILE),
    reason="set ZOHAL_TEST_NATIONAL_CODE and ZOHAL_TEST_MOBILE to check a real person",
)
def test_shahkar_against_a_real_pair(live: ZohalSync) -> None:
    # A False here is a legitimate answer, not a failure — assert only that it answered.
    assert isinstance(live.shahkar(NATIONAL_CODE, MOBILE).matched, bool)
