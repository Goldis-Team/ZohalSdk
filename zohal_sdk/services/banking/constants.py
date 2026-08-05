"""Banking (بانکی) — paths and the fixed values these endpoints define."""

CARD_INQUIRY = "/services/inquiry/card_inquiry"
CARD_TO_IBAN = "/services/inquiry/card_to_iban"
CARD_TO_ACCOUNT = "/services/inquiry/card_to_account"
ACCOUNT_TO_IBAN = "/services/inquiry/account_to_iban"
IBAN_INQUIRY = "/services/inquiry/iban"
CHECK_CARD_WITH_NAME = "/services/inquiry/check_card_with_name"
CHECK_IBAN_WITH_NAME = "/services/inquiry/check_iban_with_name"
SAYAD_CHEQUE = "/services/inquiry/check_sayad_inquiry"
SAYAD_CHEQUE_CHAIN = "/services/inquiry/check_sayad_inquiry/chain"
BOUNCED_CHEQUE = "/services/inquiry/bounced_cheque"

NATIONALITY_IRANIAN = 1
"""``nationality_type`` for an Iranian national code, on the bounced-cheque inquiry."""

NATIONALITY_FOREIGN = 2
"""``nationality_type`` for a foreign national. Zohal names the field but documents only the
Iranian value; this is the other one its upstream accepts."""

CHEQUE_TYPE_SAYADI = "1"
"""``cheque_type`` on the transfer-chain inquiry. Zohal's example sends ``"1"`` and documents no
other value, so it is the default rather than an enumeration."""

CUSTOMER_TYPES = {
    1: "حقیقی",
    2: "حقوقی",
}
"""``customer_type`` on a chain participant, decoded.

Zohal does not publish these values. The mapping is the standard Iranian banking convention —
1 a natural person, 2 a legal entity — and it is offered as
:attr:`~zohal_sdk.services.banking.data.SayadChequeCustomer.customer_type_text` beside the raw
integer, never instead of it. Where they disagree, the integer is what Zohal sent.
"""
