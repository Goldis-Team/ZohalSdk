"""Identity (احراز هویت) — the records these four endpoints return.

Dataclasses only. Three of the four answer with nothing but a verdict and reuse
:class:`~zohal_sdk.common.data.MatchResult`; only the civil-registry inquiry has a record of its
own.
"""

from dataclasses import dataclass

from zohal_sdk.common.data import InquiryRecord


@dataclass(frozen=True)
class NationalIdentity(InquiryRecord):
    """A person as the civil registry holds them (استعلام اطلاعات هویتی).

    The inquiry is a *check*, not a lookup: you supply the national code and the birth date, and
    the registry answers with the person only when the pair identifies one. ``matched`` is that
    verdict, and the name fields are meaningful only when it is ``True`` — which is why this record
    is falsy when it is not.
    """

    matched: bool = False
    """Whether the national code and birth date identify the same person."""

    national_code: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    father_name: str | None = None

    alive: bool | None = None
    """Whether the registry records the person as living."""

    is_dead: bool | None = None
    """The same fact, inverted, which Zohal sends alongside ``alive``.

    Both are reported rather than reconciled here: they are two fields in Zohal's response, and
    silently collapsing them would hide a disagreement between them from whoever needs to see it.
    Prefer ``alive``; consult ``is_dead`` only if it contradicts.
    """

    def __bool__(self) -> bool:
        return self.matched
