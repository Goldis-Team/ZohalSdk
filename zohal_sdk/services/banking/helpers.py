"""Banking (بانکی) — payload building and response reading.

Pure functions, called by both engines. Everything this SDK decides about a banking inquiry is
here, which is what keeps ``sync_engine.py`` and ``async_engine.py`` from drifting: they differ
only in which transport they call.

Note the key casing. Zohal spells the IBAN field ``IBAN`` on ``check_iban_with_name`` and in the
responses of ``card_to_iban`` and ``account_to_iban``, but ``iban`` on the ``iban`` inquiry's
request and in the Sayad cheque response. That is Zohal's inconsistency, not a typo here, and it is
why each payload names its own key rather than sharing one constant.
"""

from typing import Any

from zohal_sdk.common.data import MatchResult
from zohal_sdk.common.engine import Answer
from zohal_sdk.common.utils import (
    as_bool,
    as_dicts,
    as_int,
    as_text,
    check_card_number,
    check_digits,
    check_iban,
    check_national_code,
    check_required,
    check_sayad_id,
)
from zohal_sdk.services.banking.constants import CUSTOMER_TYPES
from zohal_sdk.services.banking.data import (
    AccountToIban,
    BouncedCheque,
    CardHolder,
    CardNameMatch,
    CardToAccount,
    CardToIban,
    IbanInfo,
    SayadCheque,
    SayadChequeChain,
    SayadChequeCustomer,
    SayadChequeLink,
)


def card_payload(card_number: str) -> dict[str, Any]:
    return {"card_number": check_card_number(card_number)}


def card_with_name_payload(card_number: str, name: str) -> dict[str, Any]:
    return {
        "card_number": check_card_number(card_number),
        "name": check_required(name, field="name", label="card holder name"),
    }


def iban_with_name_payload(iban: str, name: str) -> dict[str, Any]:
    return {
        "IBAN": check_iban(iban),
        "name": check_required(name, field="name", label="account holder name"),
    }


def iban_payload(iban: str) -> dict[str, Any]:
    return {"iban": check_iban(iban)}


def account_payload(bank_account: str, bank_code: str) -> dict[str, Any]:
    return {
        # Account numbers have no shared format across Iranian banks — length, leading zeros and
        # separators all differ — so this is normalised but not checksummed. The bank code is the
        # three-digit code from the panel's bank list.
        "bank_account": check_required(bank_account, field="bank_account", label="account number"),
        "bank_code": check_digits(bank_code, length=3, field="bank_code", label="bank code"),
    }


def sayad_payload(sayad_id: str) -> dict[str, Any]:
    return {"sayad_id": check_sayad_id(sayad_id)}


def sayad_chain_payload(sayad_id: str, national_code: str, cheque_type: str) -> dict[str, Any]:
    return {
        "sayad_id": check_sayad_id(sayad_id),
        # The issuer's national code, not the holder's — the chain is looked up from where the
        # cheque started.
        "national_code": check_national_code(national_code),
        "cheque_type": check_required(cheque_type, field="cheque_type", label="cheque type"),
    }


def bounced_cheque_payload(national_code: str, nationality_type: int) -> dict[str, Any]:
    return {
        "national_code": check_national_code(national_code),
        "nationality_type": int(nationality_type),
    }


def read_card_holder(answer: Answer) -> CardHolder:
    return CardHolder(
        name=as_text(answer.data.get("name")),
        message=answer.message,
        raw=answer.raw,
    )


def read_card_to_iban(answer: Answer) -> CardToIban:
    return CardToIban(
        iban=as_text(answer.data.get("IBAN")),
        bank_name=as_text(answer.data.get("bank_name")),
        name=as_text(answer.data.get("name")),
        message=answer.message,
        raw=answer.raw,
    )


def read_card_to_account(answer: Answer) -> CardToAccount:
    return CardToAccount(
        bank_account=as_text(answer.data.get("bank_account")),
        bank_name=as_text(answer.data.get("bank_name")),
        name=as_text(answer.data.get("name")),
        message=answer.message,
        raw=answer.raw,
    )


def read_account_to_iban(answer: Answer) -> AccountToIban:
    return AccountToIban(
        iban=as_text(answer.data.get("IBAN")),
        message=answer.message,
        raw=answer.raw,
    )


def read_iban_info(answer: Answer) -> IbanInfo:
    return IbanInfo(
        name=as_text(answer.data.get("name")),
        bank_name=as_text(answer.data.get("bank_name")),
        is_transferable=as_bool(answer.data.get("is_transferable")),
        message=answer.message,
        raw=answer.raw,
    )


def read_card_name_match(answer: Answer) -> CardNameMatch:
    return CardNameMatch(
        name=as_text(answer.data.get("name")),
        matched=as_bool(answer.data.get("matched")),
        message=answer.message,
        raw=answer.raw,
    )


def read_match(answer: Answer) -> MatchResult:
    """A yes/no answer. A missing ``matched`` is read as ``False``: this shape only ever means
    "do these belong together", and treating an absent verdict as a match would be the one
    mistake worth avoiding."""
    return MatchResult(
        matched=bool(as_bool(answer.data.get("matched"))),
        message=answer.message,
        raw=answer.raw,
    )


def read_sayad_cheque(answer: Answer) -> SayadCheque:
    data = answer.data
    return SayadCheque(
        sayad_id=as_text(data.get("sayad_id")),
        name=as_text(data.get("name")),
        iban=as_text(data.get("iban")),
        branch_code=as_text(data.get("branch_code")),
        check_type=as_text(data.get("check_type")),
        issue_date=as_text(data.get("issue_date")),
        expiration_date=as_text(data.get("expiration_date")),
        serial_no=as_text(data.get("serial_no")),
        series_no=as_text(data.get("series_no")),
        returned_cheques=as_text(data.get("returned_cheques")),
        message=answer.message,
        raw=answer.raw,
    )


def _read_chain_customer(raw: dict[str, Any]) -> SayadChequeCustomer:
    customer_type = as_int(raw.get("customer_type"))
    return SayadChequeCustomer(
        name=as_text(raw.get("name")),
        national_code=as_text(raw.get("national_code")),
        customer_type=customer_type,
        customer_type_text=CUSTOMER_TYPES.get(customer_type) if customer_type is not None else None,
    )


def _read_chain_link(raw: dict[str, Any]) -> SayadChequeLink:
    return SayadChequeLink(
        role_type=as_int(raw.get("role_type")),
        customers=tuple(_read_chain_customer(item) for item in as_dicts(raw.get("customers"))),
    )


def read_sayad_chain(answer: Answer) -> SayadChequeChain:
    return SayadChequeChain(
        links=tuple(_read_chain_link(item) for item in as_dicts(answer.data.get("chain"))),
        message=answer.message,
        raw=answer.raw,
    )


def read_bounced_cheque(answer: Answer) -> BouncedCheque:
    return BouncedCheque(
        count=as_int(answer.data.get("count")),
        message=answer.message,
        raw=answer.raw,
    )
