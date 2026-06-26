from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.schemas import (
    AnalyzeRequest,
    CaseType,
    Department,
    EvidenceVerdict,
    ReasonCode,
    Severity,
    Transaction,
)


HIGH_VALUE_BDT_THRESHOLD = float(os.environ.get("HIGH_VALUE_BDT_THRESHOLD", "50000"))


AMOUNT_PATTERN = re.compile(r"\b(\d{1,9}(?:\.\d{1,2})?)\b")
PHONE_PATTERN = re.compile(r"\+?\d{10,13}")
TXN_ID_PATTERN = re.compile(r"\bTXN-?\w+\b", re.IGNORECASE)


WRONG_TRANSFER_KEYWORDS = [
    "wrong number", "wrong recipient", "wrong person", "sent to wrong",
    "wrong account", "mistakenly sent", "by mistake", "sent by mistake",
    "wrongly sent", "incorrect number", "incorrect recipient",
    "galat number", "bhul number", "ভুল নম্বর", "ভুল নাম্বার", "ভুল রিসিভার",
]

PAYMENT_FAILED_KEYWORDS = [
    "payment failed", "transaction failed", "failed but", "deducted",
    "money deducted", "balance deducted", "didn't receive", "did not receive",
    "not received", "no credit", "not credited", "payment unsuccessful",
    "টাকা কেটে নিয়েছে", "ব্যালেন্স কমে গেছে", "পেমেন্ট ব্যর্থ",
]

REFUND_KEYWORDS = [
    "refund", "money back", "return my money", "want my money back",
    "please refund", "kindly refund", "reimburse",
    "ফেরত", "টাকা ফেরত", "রিফান্ড",
]

DUPLICATE_PAYMENT_KEYWORDS = [
    "charged twice", "deducted twice", "two times", "double charged",
    "double payment", "duplicate payment", "charged two times",
    "দুইবার কেটেছে", "দুইবার চার্জ",
]

MERCHANT_SETTLEMENT_KEYWORDS = [
    "merchant settlement", "settlement not received", "merchant payment pending",
    "merchant payout", "settlement delay", "merchant hasn't received",
    "মার্চেন্ট সেটেলমেন্ট", "মার্চেন্ট পেমেন্ট পেন্ডিং",
]

AGENT_CASH_IN_KEYWORDS = [
    "agent cash in", "cash in through agent", "agent didn't deposit",
    "agent did not deposit", "agent did not give", "agent didn't give",
    "cash deposit agent", "agent did not credit",
    "এজেন্ট ক্যাশ ইন", "এজেন্ট ডিপোজিট",
]

PHISHING_KEYWORDS = [
    "otp", "pin", "password", "share your pin", "send your otp",
    "someone called", "someone asked", "fraud call", "scam call",
    "fake sms", "phishing", "clicked the link", "shared my pin",
    "ওটিপি দিয়েছি", "পিন শেয়ার", "প্রতারণা",
]

CONTESTED_REFUND_KEYWORDS = [
    "already refunded", "not received", "didn't get", "did not get",
    "still waiting", "double charged", "no refund", "didn't receive refund",
]

LANGUAGE_BN_RANGE = re.compile(r"[\u0980-\u09FF]")


@dataclass
class RoutingDecision:
    case_type: CaseType
    severity: Severity
    department: Department
    evidence_verdict: EvidenceVerdict
    relevant_transaction_id: Optional[str]
    human_review_required: bool
    confidence: float
    reason_codes: List[ReasonCode] = field(default_factory=list)
    matched_transaction: Optional[Transaction] = None
    matched_amount: Optional[float] = None
    matched_counterparty: Optional[str] = None
    partial_match: bool = False
    needs_llm_enrichment: bool = False
    needs_llm: bool = False


@dataclass
class ExtractionResult:
    amounts: List[float] = field(default_factory=list)
    counterparties: List[str] = field(default_factory=list)
    transaction_ids: List[str] = field(default_factory=list)


def _norm(text: str) -> str:
    return (text or "").lower()


def _has_any(text: str, keywords: List[str]) -> bool:
    low = _norm(text)
    return any(k in low for k in keywords)


def detect_language(complaint: str, declared: Optional[str]) -> str:
    if declared in ("en", "bn", "mixed"):
        return declared
    if not complaint:
        return "en"
    if LANGUAGE_BN_RANGE.search(complaint):
        return "bn"
    return "en"


def extract_signals(complaint: str) -> ExtractionResult:
    out = ExtractionResult()
    if not complaint:
        return out
    for m in AMOUNT_PATTERN.finditer(complaint):
        try:
            out.amounts.append(float(m.group(1)))
        except ValueError:
            continue
    for m in PHONE_PATTERN.finditer(complaint):
        out.counterparties.append(m.group(0))
    for m in TXN_ID_PATTERN.finditer(complaint):
        out.transaction_ids.append(m.group(0).upper().replace("TXN-", "TXN-"))
    return out


def classify_case(complaint: str) -> Tuple[CaseType, List[ReasonCode]]:
    text = _norm(complaint)
    if _has_any(text, PHISHING_KEYWORDS):
        return "phishing_or_social_engineering", ["phishing_attempt"]
    if _has_any(text, WRONG_TRANSFER_KEYWORDS):
        return "wrong_transfer", ["wrong_transfer"]
    if _has_any(text, DUPLICATE_PAYMENT_KEYWORDS):
        return "duplicate_payment", ["duplicate_payment"]
    if _has_any(text, PAYMENT_FAILED_KEYWORDS):
        return "payment_failed", ["payment_failed"]
    if _has_any(text, REFUND_KEYWORDS):
        return "refund_request", ["refund_request"]
    if _has_any(text, MERCHANT_SETTLEMENT_KEYWORDS):
        return "merchant_settlement_delay", ["merchant_settlement_delay"]
    if _has_any(text, AGENT_CASH_IN_KEYWORDS):
        return "agent_cash_in_issue", ["agent_cash_in_issue"]
    return "other", []


def find_matching_transaction(
    history: List[Transaction],
    signals: ExtractionResult,
) -> Tuple[Optional[Transaction], Optional[float], Optional[str], List[ReasonCode]]:
    if not history:
        return None, None, None, []

    for txn in history:
        for tid in signals.transaction_ids:
            if tid.upper() == txn.transaction_id.upper():
                return txn, txn.amount, txn.counterparty, ["transaction_match"]

    best: Optional[Transaction] = None
    best_score = 0
    best_reasons: List[ReasonCode] = []

    for txn in history:
        score = 0
        reasons: List[ReasonCode] = []
        if signals.amounts and any(abs(a - txn.amount) < 0.01 for a in signals.amounts):
            score += 2
            reasons.append("amount_mismatch" if any(abs(a - txn.amount) >= 0.01 for a in signals.amounts) else "transaction_match")
        if signals.counterparties:
            cp_digits = re.sub(r"\D", "", txn.counterparty)
            if any(re.sub(r"\D", "", c) == cp_digits for c in signals.counterparties if len(cp_digits) >= 8):
                score += 2
                reasons.append("counterparty_unverified" if score < 4 else "counterparty_mismatch")
        if score > best_score:
            best = txn
            best_score = score
            best_reasons = reasons

    if best is None or best_score == 0:
        return None, None, None, ["no_match"]

    matched_amount = best.amount if best_score >= 2 else None
    matched_cp = best.counterparty if best_score >= 2 else None
    return best, matched_amount, matched_cp, best_reasons or ["transaction_match"]


def evaluate_evidence(
    case_type: CaseType,
    matched: Optional[Transaction],
    signals: ExtractionResult,
) -> Tuple[EvidenceVerdict, List[ReasonCode]]:
    reasons: List[ReasonCode] = []

    if case_type == "phishing_or_social_engineering":
        return "insufficient_data", ["phishing_attempt", "ambiguous_evidence"]

    if matched is None:
        if signals.amounts or signals.counterparties or signals.transaction_ids:
            return "insufficient_data", ["no_match"]
        return "insufficient_data", ["ambiguous_evidence"]

    if case_type == "payment_failed":
        if matched.status == "failed":
            return "consistent", reasons
        if matched.status == "completed":
            reasons.append("status_mismatch")
            return "inconsistent", reasons
        return "insufficient_data", ["status_mismatch"]

    if case_type == "wrong_transfer":
        if matched.status == "completed":
            return "consistent", reasons
        if matched.status in ("failed", "reversed"):
            reasons.append("status_mismatch")
            return "inconsistent", reasons
        return "insufficient_data", reasons

    if case_type == "duplicate_payment":
        same_amount_dupes = sum(
            1 for t in matched.__class__.mro().__class__ and []  # noqa
        )
        return "insufficient_data", ["duplicate_charge_detected"]

    if case_type == "refund_request":
        if matched.status in ("completed", "reversed"):
            return "consistent", reasons
        return "insufficient_data", ["ambiguous_evidence"]

    if matched.status in ("completed", "failed", "reversed"):
        return "consistent", reasons
    return "insufficient_data", ["ambiguous_evidence"]


def base_severity_and_department(case_type: CaseType) -> Tuple[Severity, Department]:
    table: Dict[CaseType, Tuple[Severity, Department]] = {
        "wrong_transfer": ("high", "dispute_resolution"),
        "payment_failed": ("high", "payments_ops"),
        "refund_request": ("low", "customer_support"),
        "duplicate_payment": ("high", "payments_ops"),
        "merchant_settlement_delay": ("medium", "merchant_operations"),
        "agent_cash_in_issue": ("high", "agent_operations"),
        "phishing_or_social_engineering": ("critical", "fraud_risk"),
        "other": ("low", "customer_support"),
    }
    return table[case_type]


def apply_escalations(
    *,
    case_type: CaseType,
    severity: Severity,
    verdict: EvidenceVerdict,
    matched: Optional[Transaction],
    complaint: str,
    human_review_required: bool,
    confidence: float,
) -> Tuple[Severity, bool, float, List[ReasonCode]]:

    extra_reasons: List[ReasonCode] = []

    if verdict == "insufficient_data":
        human_review_required = True
        confidence = min(confidence, 0.5)
        extra_reasons.append("ambiguous_evidence")

    if severity == "critical":
        human_review_required = True

    if case_type == "wrong_transfer" and matched is None:
        severity = "medium"
        extra_reasons.append("no_match")

    if case_type == "refund_request":
        text = _norm(complaint)
        if matched and matched.status in ("completed", "reversed") and _has_any(text, CONTESTED_REFUND_KEYWORDS):
            severity = "high"
            human_review_required = True
            extra_reasons.append("status_mismatch")

    if case_type == "payment_failed" and verdict == "inconsistent":
        human_review_required = True
        extra_reasons.append("status_mismatch")

    if matched is not None and matched.amount >= HIGH_VALUE_BDT_THRESHOLD:
        human_review_required = True
        extra_reasons.append("high_value_escalation")

    return severity, human_review_required, confidence, extra_reasons


def decide(req: AnalyzeRequest) -> RoutingDecision:
    complaint = req.complaint or ""

    case_type, case_reasons = classify_case(complaint)
    severity, department = base_severity_and_department(case_type)

    signals = extract_signals(complaint)
    history = req.transaction_history or []
    matched, matched_amount, matched_cp, match_reasons = find_matching_transaction(history, signals)

    verdict, verdict_reasons = evaluate_evidence(case_type, matched, signals)

    if matched is not None:
        relevant_txn_id = matched.transaction_id
    else:
        relevant_txn_id = None

    human_review_required = False
    confidence_map: Dict[EvidenceVerdict, float] = {
        "consistent": 0.9,
        "inconsistent": 0.85,
        "insufficient_data": 0.5,
    }
    confidence = confidence_map[verdict]

    severity, human_review_required, confidence, extra_reasons = apply_escalations(
        case_type=case_type,
        severity=severity,
        verdict=verdict,
        matched=matched,
        complaint=complaint,
        human_review_required=human_review_required,
        confidence=confidence,
    )

    reason_codes: List[ReasonCode] = []
    for r in case_reasons + match_reasons + verdict_reasons + extra_reasons:
        if r and r not in reason_codes:
            reason_codes.append(r)

    partial_match = (
        matched is not None
        and (
            matched_amount is None
            or matched_cp is None
            or len(signals.amounts) == 0
            or len(signals.counterparties) == 0
        )
    )
    needs_llm_enrichment = partial_match or verdict == "insufficient_data"
    needs_llm = matched is None and case_type != "phishing_or_social_engineering"

    return RoutingDecision(
        case_type=case_type,
        severity=severity,
        department=department,
        evidence_verdict=verdict,
        relevant_transaction_id=relevant_txn_id,
        human_review_required=human_review_required,
        confidence=confidence,
        reason_codes=reason_codes,
        matched_transaction=matched,
        matched_amount=matched_amount,
        matched_counterparty=matched_cp,
        partial_match=partial_match,
        needs_llm_enrichment=needs_llm_enrichment,
        needs_llm=needs_llm,
    )