# zohal-sdk

A typed Python SDK for [Zohal](https://zohal.io)'s inquiry web services — banking, identity, company and utility, video biometrics, and credit scoring — with one API surface and two interchangeable engines: **sync** and **async**.

All 37 documented endpoints, on one client. `ZohalSync` and `ZohalAsync` carry the same methods with the same arguments and the same return types; moving a call site between them is adding or removing `await`, never a rewrite.

> **Status: early development.** The API below is implemented and tested against Zohal's published response examples, but expect breaking changes before `1.0`.

## Why

Zohal's endpoints are consistent in three different ways, report failures in the *body* of a 400 or a 503, and take inputs — national codes, IBANs, card numbers, Jalali dates — that arrive from Iranian web forms with Persian digits in them. And every call is billed.

- **Every endpoint, typed** — 37 methods returning frozen dataclasses, not `dict[str, Any]`. `py.typed` shipped; clean under `mypy --strict` and `pyright` in strict mode.
- **Nothing billed for an input that cannot work** — Persian and Arabic digits are folded to ASCII, separators stripped, then national codes, company ids, IBANs and card numbers are checksum-verified locally. A bad one raises before the request goes out.
- **Two engines, same surface** — identical method names, arguments and return types on both, proven by a test that runs every endpoint through each and compares the records.
- **Failures say what happened** — one exception carrying Zohal's `result` code, its `error_code`, its own Persian message, the HTTP status and the untouched body.
- **Nothing is flattened away** — every record carries `.raw`, so a field this SDK has not modelled is still reachable.

## Installation

```bash
pip install zohal-sdk
```

Requires Python 3.10 or newer. No optional extras — Zohal is REST/JSON throughout.

## Quick start

```python
from zohal_sdk import ZohalSync

zohal = ZohalSync(token="your-api-token")

# Banking
card = zohal.card_to_iban("6362-1411-1234-5674")  # separators and Persian digits are fine
print(card.iban, card.bank_name, card.name)

# Identity — records that answer a yes/no question are falsy when the answer is no
if zohal.shahkar(national_code="0013542419", mobile="09121234567"):
    person = zohal.national_identity("0013542419", "1377/07/19")
    print(person.first_name, person.last_name, person.father_name)

# Utility
bill = zohal.bill_gas("123456789")
print(bill.amount, bill.full_name, bill.address)
```

### Async engine — FastAPI, aiohttp, anything on asyncio

The same calls, awaited:

```python
from zohal_sdk import ZohalAsync

zohal = ZohalAsync(token="your-api-token")
card = await zohal.card_to_iban("6362141112345674")
```

Concurrency is real — these overlap rather than queueing, which matters because a company or vehicle inquiry is Zohal relaying your question to a government system whose latency it does not control:

```python
import asyncio

cards = await asyncio.gather(*(zohal.card_to_iban(n) for n in card_numbers))
```

Run [`main.py`](main.py) for a tour. It makes **no network calls** by default — every Zohal endpoint is billed and there is no sandbox — so it demonstrates the validation, the record reading and the error shapes offline, against Zohal's own published examples. `python main.py --live` makes real, billed inquiries.

## Credentials

A constructor argument, always. The SDK never reads the environment.

```python
ZohalSync(token="...")
ZohalSync(token="...", timeout=30.0)  # seconds, per request
ZohalSync(token="...", base_url="http://localhost:8080")  # for a recording proxy
```

Build one client per token rather than caching one globally.

**Zohal answers only requests from IPs registered on your panel.** A `ZohalAuthenticationError` when the token is definitely right almost always means that — check **توسعه‌دهندگان → IPها** before re-issuing anything.

## The endpoints

### Banking (بانکی)

| Method | Returns |
| --- | --- |
| `card_inquiry(card_number)` | `CardHolder` — the name on the card |
| `card_to_iban(card_number)` | `CardToIban` |
| `card_to_account(card_number)` | `CardToAccount` |
| `account_to_iban(bank_account, bank_code)` | `AccountToIban` |
| `iban_inquiry(iban)` | `IbanInfo` — holder, bank, `is_transferable` |
| `check_card_with_name(card_number, name)` | `CardNameMatch` |
| `check_iban_with_name(iban, name)` | `MatchResult` |
| `sayad_cheque(sayad_id)` | `SayadCheque` |
| `sayad_cheque_chain(sayad_id, national_code)` | `SayadChequeChain` — the transfer chain, in order |
| `bounced_cheque(national_code)` | `BouncedCheque` — truthy when there *are* some |

### Identity (احراز هویت)

| Method | Returns |
| --- | --- |
| `shahkar(national_code, mobile)` | `MatchResult` — is this SIM registered to this person |
| `national_identity(national_code, birth_date)` | `NationalIdentity` |
| `check_iban_with_national_code(iban, national_code, birth_date)` | `MatchResult` |
| `check_card_with_national_code(card_number, national_code, birth_date)` | `MatchResult` |

### Utility services (خدماتی)

| Method | Returns |
| --- | --- |
| `company_inquiry(national_id)` | `Company` |
| `company_board_members(national_id)` | `BoardMembers` |
| `company_board_members_history(national_id)` | `BoardMembers` — with `end_date` filled in |
| `postal_code_inquiry(postal_code)` | `PostalAddress` |
| `vehicle_total_violations(plate_number, region_code, national_code, mobile)` | `VehicleViolationsSummary` |
| `vehicle_violations_details(...)` | `VehicleViolations` — itemised, with a summed `.total` |
| `enamad_inquiry(website)` | `Enamad` — falsy when there is no seal, or it expired |
| `persian_to_finglish(persian_text)` | `Finglish` |
| `national_card_ocr(front, back=None)` | `NationalCardOcr` |
| `voice_otp(mobile, code)` | `VoiceOtp` |
| `bill_mci` · `bill_irancell` · `bill_rightel` · `bill_fixed_line` | `MobileBill` — `mid_term` and `final_term` |
| `bill_gas(bill_id)` | `GasBill` |
| `bill_water(bill_id)` · `bill_electricity(bill_id)` | `UtilityBill` |

### Video identity verification (احراز هویت ویدیویی)

```python
media = zohal.upload_biometric_media(open("selfie.mp4", "rb"))  # path, bytes or file
session = zohal.start_liveness(
    national_code="0013542419",
    birth_date="1377/07/19",
    national_card_serial="1G34567890",
    selfie_video_id=media.id,
    callback_url="https://your-app.example/zohal/liveness",  # preferred
)
result = zohal.biometric_result(session.session_id)
if result:  # truthy only once completed *and* matched
    ...
```

`wait_for_biometric_result(session_id, timeout=180, interval=3)` polls until the session reaches a state that will not change again. Prefer the callback where you can — polling holds a thread (or a task) for as long as the video takes to process.

### Credit scoring (استعلام اعتبارسنجی)

Three steps. The OTP is the person consenting to their own credit file being pulled, so the `reference_id` must be carried through:

```python
request = zohal.credit_send_otp(national_code="0013542419", mobile="09121234567")
zohal.credit_verify_otp(request.reference_id, otp="55555")

report = zohal.wait_for_credit_result(request.reference_id, timeout=300)
print(report.score.score, report.score.risk, report.score.description)
for contract in report.direct_contracts:
    print(contract.organization_name, contract.overdue_amount)
print(report.total_overdue)
```

The report is assembled from several government systems, each contributing a section with its own status:

```python
report.personal_information  # PersonalInformation
report.score  # CreditScore, with .codes explaining it
report.direct_contracts  # facilities in their own name
report.indirect_contracts  # ones they guaranteed for somebody else
report.pichak.answered  # the cheque registry replied
report.bounced_cheque.status  # 404 = nothing on file, which is the good answer
report.judiciary.data  # bankruptcies, insolvencies, enforcement orders
report.tax.years  # one record per tax year
```

A section answering `404` means that upstream had nothing on this person. That is information, not a failure, and never raises.

## Input handling

Normalisation runs first and always: Persian `۰۱۲` and Arabic `٠١٢` digits folded to ASCII, spaces and dashes stripped, `IR` uppercased and added if omitted, mobile numbers normalised to `09XXXXXXXXX` from `+98…`, `0098…` or a bare `9…`. National codes shorter than ten digits are left-padded — spreadsheets store them as numbers and drop the leading zeros.

Then the checks, each raising `ZohalValidationError` naming the field:

| Argument | Checked |
| --- | --- |
| `national_code` | 10 digits, mod-11 check digit |
| `national_id` (company) | 11 digits, its own weighted checksum |
| `iban` | `IR` + 24 digits, ISO 13616 mod-97 |
| `card_number` | 16 digits, Luhn |
| `mobile` | normalises to `09XXXXXXXXX` |
| `birth_date` | Jalali `YYYY/MM/DD`, with real month lengths |
| `postal_code`, `sayad_id`, `bank_code` | digits, correct length |

Two deliberate gaps, both to avoid rejecting something real:

- **Esfand 30 is allowed in any year.** Which Jalali years are leap depends on which arithmetic approximation you pick, implementations disagree at the edges of the 33-year cycle, and being wrong would reject a real person's real birthday.
- **Repeated-digit national codes are allowed.** `1111111111` satisfies the published checksum. Rejecting it means encoding a convention rather than the algorithm, and a wrong rejection costs a caller the endpoint entirely, where letting one through costs a single call.

## Errors

**Everything raises, including a service-level rejection.** These are inquiries: asking again is always safe and no state at Zohal depends on the answer, so there is no reason to soften a failure into a return value.

What is *not* an error is a **negative answer**. An unmatched Shahkar, a person with three returned cheques, a pending liveness session — those are successful inquiries, and they come back as records.

```python
from zohal_sdk import (
    ZohalAuthenticationError,  # 401/403 — bad token, or your IP is not allowlisted
    ZohalConfigurationError,  # no token, nonsensical timeout — raised at construction
    ZohalError,  # base for everything above
    ZohalNetworkError,  # timeout, connection refused, undecodable body
    ZohalPollTimeoutError,  # a wait_for_* helper ran out of budget  (.reference, .last_status)
    ZohalServiceError,  # reached and declined  (.result, .error_code, .status, .raw)
    ZohalValidationError,  # refused locally; nothing was billed  (.field, .value)
)

try:
    person = zohal.national_identity(national_code, birth_date)
except ZohalValidationError as exc:
    # No call was made. exc.field names the argument at fault.
    form.add_error(exc.field, str(exc))
except ZohalServiceError as exc:
    log.warning("declined: %s (result=%s code=%s) raw=%s", exc, exc.result, exc.error_code, exc.raw)
```

`ZohalServiceError` carries Zohal's own Persian message, which is written for whoever has to fix the input and usually names the field.

**The HTTP status decides nothing on its own.** Zohal reports `result=6` under 503 for a service that is down, `result=5` under 500, `result=6` under 404 and `result=6` under 400 — all in the same envelope. The SDK reads the body at any status. The single exception is 401/403, which becomes `ZohalAuthenticationError` before the body is consulted.

## How the code is laid out

The client is flat — 37 methods on one object — but the code behind it is split per service family:

```
zohal_sdk/
  client.py              ZohalSync / ZohalAsync — the five mixins composed
  common/
    constants.py         base URL, timeout, result codes
    data.py              ZohalConfig, InquiryRecord, MatchResult — dataclasses only
    exceptions.py        the error hierarchy
    envelope.py          the three response shapes → a data dict, or an exception
    http.py              post/get/multipart, in both flavours
    engine.py            SyncEngine / AsyncEngine — transport paired with envelope
    utils.py             normalisation, the checksums, the coercions
  services/
    banking/  identity/  utility/  biometric/  credit/
```

Each family holds the same five files: `constants.py` (paths and fixed values), `data.py` (records — dataclasses only), `helpers.py` (the pure functions that build payloads and read responses), and `sync_engine.py` / `async_engine.py`, which are thin shells over both. Every decision about what Zohal said lives in `helpers.py` and is shared by both engines, which is why they cannot drift — and [`tests/test_engines_agree.py`](tests/test_engines_agree.py) runs every endpoint through both and asserts the records compare equal.

## Tests

```bash
pytest
```

Offline by default, and fast. Every response fixture in [`tests/data/openapi_examples.json`](tests/data/openapi_examples.json) is lifted verbatim from the examples in Zohal's own OpenAPI document, so the record readers are checked against what Zohal says it sends rather than against something written to match the code.

## License

MIT — see [LICENSE](LICENSE).
