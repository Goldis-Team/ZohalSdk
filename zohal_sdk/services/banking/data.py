"""Banking (بانکی) — the records these ten endpoints return.

Dataclasses only. Paths and fixed values live in ``constants.py``; the functions that build
payloads and read responses live in ``helpers.py``.

All ten answer in Zohal's standard inquiry envelope, so every record here subclasses
:class:`~zohal_sdk.common.data.InquiryRecord` and carries its ``message`` and ``raw`` alongside its
own fields.
"""

from dataclasses import dataclass

from zohal_sdk.common.data import InquiryRecord


@dataclass(frozen=True)
class CardHolder(InquiryRecord):
    """The name on a card (استعلام نام صاحب کارت)."""

    name: str | None = None
    """The card holder's name as the issuing bank records it."""


@dataclass(frozen=True)
class CardToIban(InquiryRecord):
    """A card number resolved to its IBAN (تبدیل کارت به شبا)."""

    iban: str | None = None
    """The IBAN the card settles to."""

    bank_name: str | None = None
    """The issuing bank, in Persian."""

    name: str | None = None
    """The account holder's name."""


@dataclass(frozen=True)
class CardToAccount(InquiryRecord):
    """A card number resolved to its account number (تبدیل کارت به حساب)."""

    bank_account: str | None = None
    """The account number behind the card, in the issuing bank's own format."""

    bank_name: str | None = None
    name: str | None = None


@dataclass(frozen=True)
class AccountToIban(InquiryRecord):
    """An account number resolved to its IBAN (تبدیل حساب به شبا)."""

    iban: str | None = None


@dataclass(frozen=True)
class IbanInfo(InquiryRecord):
    """What an IBAN belongs to (استعلام شبا)."""

    name: str | None = None
    """The account holder — a person, or an organisation."""

    bank_name: str | None = None

    is_transferable: bool | None = None
    """Whether the account can receive a transfer.

    ``False`` is a real answer about a real account — blocked, closed, or of a type that does not
    accept incoming settlement — and is worth checking before paying out to it.
    """


@dataclass(frozen=True)
class CardNameMatch(InquiryRecord):
    """A card checked against a name (تطابق کارت و نام صاحب کارت).

    Zohal documents this response as carrying the holder's ``name`` and nothing else, which makes
    the comparison yours to do — compare it against the name you sent, allowing for how Iranian
    names get written down. ``matched`` is populated only if Zohal sends such a field, which its
    published response does not; it is here so that a caller reads a boolean rather than nothing
    should that change.
    """

    name: str | None = None
    """The holder's name as the bank records it."""

    matched: bool | None = None
    """Zohal's own verdict, where it sends one. ``None`` means it sent none — use ``name``."""


@dataclass(frozen=True)
class SayadCheque(InquiryRecord):
    """A Sayad cheque (استعلام چک صیادی)."""

    sayad_id: str | None = None
    name: str | None = None
    """The issuer's name."""

    iban: str | None = None
    """The IBAN the cheque is drawn on."""

    branch_code: str | None = None
    check_type: str | None = None
    """The cheque's type code, e.g. ``"BANS"``."""

    issue_date: str | None = None
    """Jalali, as Zohal sends it — unpadded, e.g. ``"1370/1/1"``."""

    expiration_date: str | None = None
    serial_no: str | None = None
    series_no: str | None = None
    returned_cheques: str | None = None
    """Any returned-cheque note against this one. Usually empty, which is reported as ``None``."""


@dataclass(frozen=True)
class SayadChequeCustomer:
    """One party to a link in a cheque's transfer chain."""

    name: str | None = None
    """The person's or company's name."""

    national_code: str | None = None
    """Their national code, or the company's national id."""

    customer_type: int | None = None
    """Zohal's raw type code."""

    customer_type_text: str | None = None
    """The code read through
    :data:`~zohal_sdk.services.banking.constants.CUSTOMER_TYPES` — a convention, not something
    Zohal publishes. ``None`` for a code that mapping does not cover."""


@dataclass(frozen=True)
class SayadChequeLink:
    """One hop in a cheque's transfer chain."""

    role_type: int | None = None
    """The party's role at this hop. Zohal sends these in chain order — its own example runs
    1, 2, 3 down a three-hop chain — and does not publish what each number names, so the value is
    passed through as it arrived rather than guessed at."""

    customers: tuple[SayadChequeCustomer, ...] = ()
    """Everyone holding that role at this hop; more than one where a cheque is jointly held."""


@dataclass(frozen=True)
class SayadChequeChain(InquiryRecord):
    """A cheque's transfer chain (استعلام زنجیره انتقالات چک صیادی).

    ``links`` is in the order Zohal sent it, which is the order the cheque moved.
    """

    links: tuple[SayadChequeLink, ...] = ()


@dataclass(frozen=True)
class BouncedCheque(InquiryRecord):
    """How many returned cheques stand against a person (استعلام چک برگشتی)."""

    count: int | None = None
    """Zero is the answer you are usually hoping for, and is a successful inquiry."""

    def __bool__(self) -> bool:
        """Truthy when there *are* returned cheques, so ``if client.bounced_cheque(...):`` reads
        as "does this person have any"."""
        return bool(self.count)
