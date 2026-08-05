"""A guided tour of zohal-sdk.

    python main.py           # offline: validation, normalisation, records, errors — costs nothing
    python main.py --live    # makes real, billed inquiries; needs ZOHAL_TOKEN

Zohal has no sandbox and every endpoint is billed per call, so the default tour makes no network
requests at all. It exercises the half of the SDK that runs before the wire — the digit folding and
the checksums — and then shows how a response is turned into a record, using Zohal's own published
examples.

``--live`` is the opposite: it spends real money on your account, one inquiry per endpoint it
touches, and it only works from an IP registered on your panel.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

from zohal_sdk import (
    ZohalServiceError,
    ZohalSync,
    ZohalValidationError,
)
from zohal_sdk.common.engine import Answer
from zohal_sdk.common.envelope import read_data
from zohal_sdk.common.utils import (
    check_card_number,
    check_iban,
    check_mobile,
    check_national_code,
)
from zohal_sdk.services.banking import helpers as banking

EXAMPLES = Path(__file__).parent / "tests" / "data" / "openapi_examples.json"


def heading(text: str) -> None:
    print(f"\n\033[1m{text}\033[0m")
    print("─" * len(text))


def tour_normalisation() -> None:
    heading("Normalisation — what a web form actually hands you")
    for written in ("۶۳۶۲-۱۴۱۱-۱۲۳۴-۵۶۷۴", "6362 1411 1234 5674", "6362141112345674"):
        print(f"  {written:<26} → {check_card_number(written)}")
    for written in ("+989121234567", "00989121234567", "9121234567"):
        print(f"  {written:<26} → {check_mobile(written)}")
    print(f"  {'820540102680020817909002':<26} → {check_iban('820540102680020817909002')}")
    print(f"  {'13542419 (Excel-mangled)':<26} → {check_national_code('13542419')}")


def tour_validation() -> None:
    heading("Validation — refused locally, so the call is never billed")
    attempts: list[tuple[str, Any]] = [
        ("card failing Luhn", lambda: check_card_number("6362141112345678")),
        ("national code failing mod-11", lambda: check_national_code("0013542418")),
        ("IBAN failing mod-97", lambda: check_iban("IR820540102680020817909003")),
        ("mobile that is a landline", lambda: check_mobile("02191097734")),
    ]
    for label, attempt in attempts:
        try:
            attempt()
        except ZohalValidationError as exc:
            print(f"  {label:<30} → {exc}")


def tour_records() -> None:
    heading("Records — Zohal's own published examples, read into typed objects")
    examples: dict[str, dict[str, Any]] = json.loads(EXAMPLES.read_text(encoding="utf-8"))

    body = examples["/services/inquiry/card_to_iban"]["200"]
    card = banking.read_card_to_iban(Answer(body["response_body"]["data"], body))
    print(f"  card_to_iban   → iban={card.iban} bank={card.bank_name} name={card.name}")

    body = examples["/services/inquiry/check_sayad_inquiry/chain"]["200"]
    chain = banking.read_sayad_chain(Answer(body["response_body"]["data"], body))
    print(f"  cheque chain   → {len(chain.links)} hops")
    for link in chain.links:
        who = ", ".join(f"{c.name} ({c.customer_type_text})" for c in link.customers)
        print(f"                   role {link.role_type}: {who}")

    body = examples["/services/inquiry/bounced_cheque"]["200"]
    cheques = banking.read_bounced_cheque(Answer(body["response_body"]["data"], body))
    print(f"  bounced cheque → count={cheques.count}, record is {'truthy' if cheques else 'falsy'}")


def tour_errors() -> None:
    heading("Errors — a rejection carries Zohal's own message and code")
    examples: dict[str, dict[str, Any]] = json.loads(EXAMPLES.read_text(encoding="utf-8"))
    body = examples["/services/inquiry/company_inquiry"]["400"]
    try:
        read_data(body, status=400, service="company_inquiry")
    except ZohalServiceError as exc:
        print(f"  raised   : {exc}")
        print(f"  .result  : {exc.result}")
        print(f"  .error_code: {exc.error_code}")
        print(f"  .status  : {exc.status}")


def tour_live(token: str) -> None:
    heading("Live inquiries — these are billed to your account")
    zohal = ZohalSync(token=token)

    national_code = os.environ.get("ZOHAL_DEMO_NATIONAL_CODE")
    mobile = os.environ.get("ZOHAL_DEMO_MOBILE")
    website = os.environ.get("ZOHAL_DEMO_WEBSITE", "zohal.io")

    print(f"  enamad_inquiry({website!r})")
    seal = zohal.enamad_inquiry(website)
    print(f"    → {seal.name} · level {seal.logo_level} · expired={seal.expired}")

    if national_code and mobile:
        print(f"  shahkar({national_code!r}, {mobile!r})")
        print(f"    → matched={zohal.shahkar(national_code, mobile).matched}")
    else:
        print("  shahkar — skipped; set ZOHAL_DEMO_NATIONAL_CODE and ZOHAL_DEMO_MOBILE to run it")


def main() -> int:
    live = "--live" in sys.argv

    tour_normalisation()
    tour_validation()
    tour_records()
    tour_errors()

    if not live:
        heading("Live inquiries")
        print("  Skipped. Every Zohal endpoint is billed per call, so this tour stays offline")
        print("  unless you ask for it:  python main.py --live   (needs ZOHAL_TOKEN)")
        return 0

    # The SDK never reads the environment — only this script does, and only for the demo.
    token = os.environ.get("ZOHAL_TOKEN", "").strip()
    if not token:
        print("\nZOHAL_TOKEN is not set. --live needs a real token, from an allowlisted IP.")
        return 1
    try:
        tour_live(token)
    except ZohalServiceError as exc:
        print(f"\nZohal declined: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
