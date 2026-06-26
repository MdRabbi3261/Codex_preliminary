from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple


_CREDENTIAL_WORDS = [
    "pin", "otp", "password", "passcode", "cvv", "cvc",
    "card number", "credit card number", "debit card number",
    "full card", "card no", "card-number", "access token",
    "security code", "verification code",
]

_CREDENTIAL_REQUEST_PHRASES = [
    "share your pin", "send your pin", "give me your pin", "tell me your pin",
    "share your otp", "send your otp", "give me your otp", "tell me your otp",
    "share your password", "send your password", "give me your password",
    "share your cvv", "send your cvv",
    "share your card number", "send your card number",
    "kindly share your", "please share your",
    "verify your identity by sending",
    "confirm your pin", "confirm your otp", "confirm your password",
    "enter your pin", "enter your otp", "enter your password",
    "type your pin", "type your password",
]

_FINANCIAL_COMMITMENT_PHRASES = [
    "we have reversed your transaction",
    "we have reversed the transaction",
    "your transaction has been reversed",
    "the transaction has been reversed",
    "your money has been refunded",
    "your money will be refunded",
    "we will refund you",
    "we will refund your money",
    "we have refunded",
    "refund has been processed",
    "refund is processed",
    "we will unlock your profile",
    "we have unlocked your account",
    "your account has been unlocked",
    "we will release the hold",
    "funds have been released",
    "we have credited your account",
    "amount has been credited",
    "we will recover your money",
    "we have recovered your money",
    "guaranteed refund",
    "100% refund",
]

_THIRD_PARTY_CONTACT_PHRASES = [
    "contact our agent", "contact the agent", "call the agent",
    "contact our executive", "call our executive", "call our representative",
    "whatsapp our agent", "message our agent on",
    "telegram", "viber", "imo", "signal",
    "facebook messenger", "fb messenger", "instagram dm",
    "send sms to", "text us at",
    "email us at gmail", "mail us at yahoo",
    "contact us on personal",
    "outside this chat", "off platform",
    "personal phone", "personal number", "personal email",
    "bypass official", "skip official",
]

_INJECTION_PATTERNS = [
    r"ignore (the )?(previous|above|prior) instructions?",
    r"ignore (all )?previous prompts?",
    r"disregard (the )?(previous|above|system) (instructions?|prompts?)",
    r"forget (everything|all) (above|previous)",
    r"you are now",
    r"act as",
    r"pretend to be",
    r"new instructions?:",
    r"system prompt:",
    r"reveal (your|the) (system|hidden) prompt",
    r"output (the )?(json|schema) (as|in) (a )?different",
    r"override (the )?(rules|guardrails|safety)",
    r"do not follow (the )?(rules|safety)",
    r"bypass (the )?(safety|filter)",
]


@dataclass
class SafetyVerdict:
    safe: bool
    cleaned_text: str
    triggered_rules: List[str]
    injection_detected: bool


def _lower(text: str) -> str:
    return text.lower()


def _any_phrase(haystack: str, needles: List[str]) -> bool:
    return any(n in haystack for n in needles)


def _any_regex(haystack: str, patterns: List[str]) -> bool:
    return any(re.search(p, haystack) for p in patterns)


def detect_injection(text: str) -> bool:
    if not text:
        return False
    lower = _lower(text)
    if _any_regex(lower, _INJECTION_PATTERNS):
        return True
    return False


def sanitize_reply(
    reply: str,
    *,
    language: str = "en",
) -> Tuple[str, List[str]]:
    if not reply:
        return reply, []

    triggered: List[str] = []
    cleaned = reply

    lower = _lower(cleaned)

    if _any_phrase(lower, _CREDENTIAL_REQUEST_PHRASES) or _contains_credential_word_with_request(cleaned):
        triggered.append("credential_request_blocked")
        cleaned = _strip_credential_requests(cleaned)

    if _any_phrase(_lower(cleaned), _FINANCIAL_COMMITMENT_PHRASES):
        triggered.append("financial_commitment_blocked")
        cleaned = _replace_financial_commitments(cleaned)

    if _any_phrase(_lower(cleaned), _THIRD_PARTY_CONTACT_PHRASES):
        triggered.append("third_party_contact_blocked")
        cleaned = _strip_third_party_contacts(cleaned, language=language)

    return cleaned, triggered


def _contains_credential_word_with_request(text: str) -> bool:
    lower = _lower(text)
    request_markers = ["share", "send", "give", "tell", "enter", "type", "provide", "submit", "confirm your", "kindly"]
    has_request = any(m in lower for m in request_markers)
    if not has_request:
        return False
    return any(re.search(rf"\b{re.escape(w)}\b", lower) for w in _CREDENTIAL_WORDS)


_CREDENTIAL_REPLACEMENTS = [
    (r"kindly share your [a-z0-9 \-]{1,40}", "We will never ask for your credentials."),
    (r"please share your [a-z0-9 \-]{1,40}", "We will never ask for your credentials."),
    (r"share your [a-z0-9 \-]{1,40}", "We will never ask for your credentials."),
    (r"send your [a-z0-9 \-]{1,40}", "We will never ask for your credentials."),
    (r"give (me )?your [a-z0-9 \-]{1,40}", "We will never ask for your credentials."),
    (r"tell me your [a-z0-9 \-]{1,40}", "We will never ask for your credentials."),
    (r"enter your [a-z0-9 \-]{1,40}", "We will never ask for your credentials."),
    (r"type your [a-z0-9 \-]{1,40}", "We will never ask for your credentials."),
    (r"confirm your [a-z0-9 \-]{1,40}", "We will never ask for your credentials."),
    (r"verify your identity by sending [a-z0-9 \-]{1,40}", "Verification is handled inside this official chat only."),
]


def _strip_credential_requests(text: str) -> str:
    cleaned = text
    for pattern, replacement in _CREDENTIAL_REPLACEMENTS:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    return cleaned


_FINANCIAL_REPLACEMENTS = [
    (r"we have reversed your transaction[^.]*\.", "Any eligible amount will be returned through official channels after review."),
    (r"we have reversed the transaction[^.]*\.", "Any eligible amount will be returned through official channels after review."),
    (r"your transaction has been reversed[^.]*\.", "Any eligible amount will be returned through official channels after review."),
    (r"the transaction has been reversed[^.]*\.", "Any eligible amount will be returned through official channels after review."),
    (r"your money has been refunded[^.]*\.", "Any eligible amount will be returned through official channels after review."),
    (r"your money will be refunded[^.]*\.", "Any eligible amount will be returned through official channels after review."),
    (r"we will refund you[^.]*\.", "Any eligible amount will be returned through official channels after review."),
    (r"we will refund your money[^.]*\.", "Any eligible amount will be returned through official channels after review."),
    (r"we have refunded[^.]*\.", "Any eligible amount will be returned through official channels after review."),
    (r"refund has been processed[^.]*\.", "The operational division will cross-reference this ledger sequence."),
    (r"refund is processed[^.]*\.", "The operational division will cross-reference this ledger sequence."),
    (r"we will unlock your profile[^.]*\.", "The operational division will cross-reference this account state."),
    (r"we have unlocked your account[^.]*\.", "The operational division will cross-reference this account state."),
    (r"your account has been unlocked[^.]*\.", "The operational division will cross-reference this account state."),
    (r"we will release the hold[^.]*\.", "The operational division will cross-reference this account state."),
    (r"funds have been released[^.]*\.", "The operational division will cross-reference this ledger sequence."),
    (r"we have credited your account[^.]*\.", "The operational division will cross-reference this ledger sequence."),
    (r"amount has been credited[^.]*\.", "The operational division will cross-reference this ledger sequence."),
    (r"we will recover your money[^.]*\.", "The operational division will cross-reference this ledger sequence."),
    (r"we have recovered your money[^.]*\.", "The operational division will cross-reference this ledger sequence."),
    (r"guaranteed refund", "a review for any eligible return through official channels"),
    (r"100% refund", "a review for any eligible return through official channels"),
]


def _replace_financial_commitments(text: str) -> str:
    cleaned = text
    for pattern, replacement in _FINANCIAL_REPLACEMENTS:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    return cleaned


_THIRD_PARTY_REPLACEMENTS_EN = [
    (r"contact our agent[^.]*\.", "Please continue this conversation here in the official support channel."),
    (r"contact the agent[^.]*\.", "Please continue this conversation here in the official support channel."),
    (r"call the agent[^.]*\.", "Please continue this conversation here in the official support channel."),
    (r"contact our executive[^.]*\.", "Please continue this conversation here in the official support channel."),
    (r"call our executive[^.]*\.", "Please continue this conversation here in the official support channel."),
    (r"call our representative[^.]*\.", "Please continue this conversation here in the official support channel."),
    (r"whatsapp our agent[^.]*\.", "Please continue this conversation here in the official support channel."),
    (r"message our agent on[^.]*\.", "Please continue this conversation here in the official support channel."),
    (r"\b(?:telegram|viber|imo|signal)\b[^.]*\.", "Please continue this conversation here in the official support channel."),
    (r"facebook messenger[^.]*\.", "Please continue this conversation here in the official support channel."),
    (r"fb messenger[^.]*\.", "Please continue this conversation here in the official support channel."),
    (r"instagram dm[^.]*\.", "Please continue this conversation here in the official support channel."),
    (r"send sms to[^.]*\.", "Please continue this conversation here in the official support channel."),
    (r"text us at[^.]*\.", "Please continue this conversation here in the official support channel."),
    (r"email us at gmail[^.]*\.", "Please continue this conversation here in the official support channel."),
    (r"mail us at yahoo[^.]*\.", "Please continue this conversation here in the official support channel."),
    (r"contact us on personal[^.]*\.", "Please continue this conversation here in the official support channel."),
    (r"outside this chat[^.]*\.", "Please continue this conversation here in the official support channel."),
    (r"off platform[^.]*\.", "Please continue this conversation here in the official support channel."),
    (r"personal phone[^.]*\.", "Please continue this conversation here in the official support channel."),
    (r"personal number[^.]*\.", "Please continue this conversation here in the official support channel."),
    (r"personal email[^.]*\.", "Please continue this conversation here in the official support channel."),
    (r"bypass official[^.]*\.", "Please continue this conversation here in the official support channel."),
    (r"skip official[^.]*\.", "Please continue this conversation here in the official support channel."),
]

_THIRD_PARTY_REPLACEMENTS_BN = [
    (r"এজেন্টের সাথে যোগাযোগ[^।]*।", "অনুগ্রহ করে এই সরকারি সাপোর্ট চ্যানেলে কথোপকথন চালিয়ে যান।"),
    (r"ব্যক্তিগত নম্বরে[^।]*।", "অনুগ্রহ করে এই সরকারি সাপোর্ট চ্যানেলে কথোপকথন চালিয়ে যান।"),
    (r"টেলিগ্রাম[^।]*।", "অনুগ্রহ করে এই সরকারি সাপোর্ট চ্যানেলে কথোপকথন চালিয়ে যান।"),
    (r"হোয়াটসঅ্যাপ[^।]*।", "অনুগ্রহ করে এই সরকারি সাপোর্ট চ্যানেলে কথোপকথন চালিয়ে যান।"),
]


def _strip_third_party_contacts(text: str, *, language: str) -> str:
    cleaned = text
    rules = _THIRD_PARTY_REPLACEMENTS_EN if language != "bn" else _THIRD_PARTY_REPLACEMENTS_BN
    for pattern, replacement in rules:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    return cleaned


def enforce_safety(
    reply: str,
    complaint: str,
    *,
    language: str = "en",
) -> SafetyVerdict:
    injection = detect_injection(complaint)
    cleaned, triggered = sanitize_reply(reply, language=language)
    return SafetyVerdict(
        safe=(len(triggered) == 0 and not injection),
        cleaned_text=cleaned,
        triggered_rules=triggered,
        injection_detected=injection,
    )


def safe_complaint_excerpt(text: str, *, max_chars: int = 4000) -> str:
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    head_budget = max_chars - 1000 - 25
    if head_budget < 1000:
        head_budget = max_chars // 2
    head = text[:head_budget]
    tail = text[-(max_chars - head_budget - 25):]
    return f"{head}\n\n…[truncated]…\n\n{tail}"
