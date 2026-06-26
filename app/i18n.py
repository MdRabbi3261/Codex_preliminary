from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.routing import RoutingDecision


_FALLBACK_EN = "Your ticket has been received and routed to the appropriate team. Reference: {ref_id}."

_FALLBACK_BN = "আপনার অভিযোগ গ্রহণ করা হয়েছে এবং যথাযথ টিমের কাছে পাঠানো হয়েছে। রেফারেন্স: {ref_id}।"


_TEMPLATES_EN = {
    "wrong_transfer": (
        "We see the transfer of {amount} BDT to {counterparty} on {date}. "
        "Our dispute team will contact the recipient within 2 business hours. "
        "Reference: {ref_id}."
    ),
    "payment_failed": (
        "The transaction {txn_id} of {amount} BDT shows status {status}. "
        "Our payments team is investigating and will update you within 24 hours. "
        "Reference: {ref_id}."
    ),
    "duplicate_payment": (
        "We detected a possible double charge of {amount} BDT on {date}. "
        "A refund will be processed within 5 business days if confirmed. "
        "Reference: {ref_id}."
    ),
    "refund_request": (
        "Your refund request for {amount} BDT (transaction {txn_id}) has been logged. "
        "You will receive confirmation within 3 business days. "
        "Reference: {ref_id}."
    ),
    "merchant_settlement_delay": (
        "Merchant settlement for {amount} BDT on {date} is pending verification. "
        "Our merchant operations team will follow up within 48 hours. "
        "Reference: {ref_id}."
    ),
    "agent_cash_in_issue": (
        "The cash-in through agent for {amount} BDT on {date} is under review. "
        "Our agent operations team will reconcile within 24 hours. "
        "Reference: {ref_id}."
    ),
    "phishing_or_social_engineering": (
        "We have flagged this as a suspected fraud attempt. "
        "Please do not share OTP, PIN, or password with anyone. "
        "Our fraud team will contact you within 1 hour. "
        "Reference: {ref_id}."
    ),
    "other": _FALLBACK_EN,
}


_TEMPLATES_BN = {
    "wrong_transfer": (
        "{date} তারিখে {counterparty}-এ {amount} টাকা পাঠানোর রেকর্ড পাওয়া গেছে। "
        "আমাদের বিতর্ক দল ২ কার্যদিবসের মধ্যে প্রাপকের সাথে যোগাযোগ করবে। "
        "রেফারেন্স: {ref_id}।"
    ),
    "payment_failed": (
        "{txn_id} লেনদেনের {amount} টাকা {status} অবস্থায় আছে। "
        "আমাদের পেমেন্টস টিম তদন্ত করে ২৪ ঘন্টার মধ্যে আপডেট দেবে। "
        "রেফারেন্স: {ref_id}।"
    ),
    "duplicate_payment": (
        "{date} তারিখে {amount} টাকা দুইবার কেটে যাওয়ার সম্ভাবনা শনাক্ত হয়েছে। "
        "নিশ্চিত হলে ৫ কার্যদিবসের মধ্যে রিফান্ড করা হবে। "
        "রেফারেন্স: {ref_id}।"
    ),
    "refund_request": (
        "{amount} টাকার রিফান্ড অনুরোধ (লেনদেন {txn_id}) গ্রহণ করা হয়েছে। "
        "৩ কার্যদিবসের মধ্যে নিশ্চিতকরণ পাবেন। "
        "রেফারেন্স: {ref_id}।"
    ),
    "merchant_settlement_delay": (
        "{date} তারিখে মার্চেন্ট সেটেলমেন্ট {amount} টাকা যাচাইয়ের অপেক্ষায় আছে। "
        "মার্চেন্ট অপারেশনস টিম ৪৮ ঘন্টার মধ্যে ফলো-আপ করবে। "
        "রেফারেন্স: {ref_id}।"
    ),
    "agent_cash_in_issue": (
        "{date} তারিখে এজেন্টের মাধ্যমে {amount} টাকা ক্যাশ-ইন পর্যালোচনাধীন। "
        "এজেন্ট অপারেশনস টিম ২৪ ঘন্টার মধ্যে মিলিয়ে দেবে। "
        "রেফারেন্স: {ref_id}।"
    ),
    "phishing_or_social_engineering": (
        "এটি সম্ভাব্য প্রতারণামূলক ঘটনা হিসেবে চিহ্নিত হয়েছে। "
        "অনুগ্রহ করে কাউকে OTP, PIN বা পাসওয়ার্ড শেয়ার করবেন না। "
        "আমাদের ফ্রড টিম ১ ঘন্টার মধ্যে যোগাযোগ করবে। "
        "রেফারেন্স: {ref_id}।"
    ),
    "other": _FALLBACK_BN,
}


_AGENT_SUMMARY_EN = (
    "Case {ref_id}: {case_type} | severity={severity} | department={department} | "
    "evidence={evidence_verdict} | human_review={human_review_required} | "
    "confidence={confidence:.2f} | reasons={reasons}"
)


_AGENT_SUMMARY_BN = (
    "কেস {ref_id}: {case_type} | গুরুত্ব={severity} | বিভাগ={department} | "
    "প্রমাণ={evidence_verdict} | মানব পর্যালোচনা={human_review_required} | "
    "আত্মবিশ্বাস={confidence:.2f} | কারণ={reasons}"
)


_NEXT_ACTION_EN = {
    "wrong_transfer": "Dispute team: contact recipient within 2 hours, freeze if not yet credited.",
    "payment_failed": "Payments ops: pull gateway logs for txn {txn_id}, reconcile within 24 hours.",
    "duplicate_payment": "Payments ops: confirm duplicate charge, initiate refund within 5 business days.",
    "refund_request": "Customer support: verify refund status and respond within 3 business days.",
    "merchant_settlement_delay": "Merchant ops: verify settlement file and update merchant within 48 hours.",
    "agent_cash_in_issue": "Agent ops: reconcile agent ledger and respond within 24 hours.",
    "phishing_or_social_engineering": "Fraud risk: escalate immediately, advise customer not to share credentials.",
    "other": "Customer support: triage and assign within SLA.",
}


_NEXT_ACTION_BN = {
    "wrong_transfer": "বিতর্ক দল: ২ ঘন্টার মধ্যে প্রাপকের সাথে যোগাযোগ করুন, এখনও জমা না হলে ফ্রিজ করুন।",
    "payment_failed": "পেমেন্টস অপস: txn {txn_id}-এর গেটওয়ে লগ দেখুন, ২৪ ঘন্টার মধ্যে মিলান।",
    "duplicate_payment": "পেমেন্টস অপস: ডুপ্লিকেট চার্জ নিশ্চিত করুন, ৫ কার্যদিবসে রিফান্ড শুরু করুন।",
    "refund_request": "কাস্টমার সাপোর্ট: রিফান্ডের অবস্থা যাচাই করুন এবং ৩ কার্যদিবসে উত্তর দিন।",
    "merchant_settlement_delay": "মার্চেন্ট অপস: সেটেলমেন্ট ফাইল যাচাই করুন এবং ৪৮ ঘন্টার মধ্যে মার্চেন্টকে আপডেট দিন।",
    "agent_cash_in_issue": "এজেন্ট অপস: এজেন্ট লেজার মিলান এবং ২৪ ঘন্টার মধ্যে উত্তর দিন।",
    "phishing_or_social_engineering": "ফ্রড রিস্ক: অবিলম্বে এসকেলেট করুন, কাস্টমারকে ক্রেডেনশিয়াল শেয়ার না করতে পরামর্শ দিন।",
    "other": "কাস্টমার সাপোর্ট: SLA-র মধ্যে ট্রায়াজ করুন এবং বরাদ্দ করুন।",
}


_SYSTEM_PROMPT_EN = (
    "You are QueueStorm Investigator, a careful fintech customer-support assistant for bKash. "
    "You draft replies in English (or Bangla if complaint_lang=bn) on behalf of agents. "
    "Hard rules:\n"
    "- Never request or echo OTPs, PINs, passwords, or card numbers.\n"
    "- Never commit to refunds, reversals, or settlements without human approval.\n"
    "- Never direct the customer to contact a third party (bank, police, etc.).\n"
    "- Never promise amounts or timelines beyond the policy limits stated.\n"
    "- Keep the reply under 80 words.\n"
    "- Output ONLY the customer_reply text, no preamble, no JSON, no markdown."
)


_SYSTEM_PROMPT_BN = (
    "আপনি QueueStorm Investigator, বিকাশের জন্য একটি সতর্ক ফিনটেক কাস্টমার সাপোর্ট সহকারী। "
    "আপনি এজেন্টের পক্ষে ইংরেজি (বা অভিযোগ ভাষা বাংলা হলে বাংলায়) উত্তর তৈরি করেন। "
    "কঠোর নিয়ম:\n"
    "- কখনও OTP, PIN, পাসওয়ার্ড বা কার্ড নম্বর চাইবেন না বা প্রতিধ্বনিত করবেন না।\n"
    "- মানব অনুমোদন ছাড়া রিফান্ড, রিভার্সাল বা সেটেলমেন্টের প্রতিশ্রুতি দেবেন না।\n"
    "- কাস্টমারকে তৃতীয় পক্ষের (ব্যাংক, পুলিশ ইত্যাদি) সাথে যোগাযোগ করতে বলবেন না।\n"
    "- নীতিমালার বাইরে কোনো পরিমাণ বা সময়সীমার প্রতিশ্রুতি দেবেন না।\n"
    "- উত্তর ৮০ শব্দের মধ্যে রাখুন।\n"
    "- শুধুমাত্র customer_reply টেক্সট দিন, কোনো ভূমিকা, JSON বা মার্কডাউন নয়।"
)


def _format_date(iso_date: Optional[str]) -> str:
    if not iso_date:
        return "the recorded date"
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return iso_date[:10] if len(iso_date) >= 10 else "the recorded date"


def build_customer_reply(
    *,
    language: str,
    decision,
    ref_id: str,
    matched_txn: Optional[object] = None,
) -> str:
    is_bn = language == "bn"
    table = _TEMPLATES_BN if is_bn else _TEMPLATES_EN
    template = table.get(decision.case_type, _FALLBACK_BN if is_bn else _FALLBACK_EN)

    txn_id = decision.relevant_transaction_id or "N/A"
    if matched_txn is not None:
        amount = getattr(matched_txn, "amount", None)
        cp = getattr(matched_txn, "counterparty", None)
        date_str = _format_date(getattr(matched_txn, "timestamp", None))
        status = getattr(matched_txn, "status", "unknown")
    else:
        amount = None
        cp = None
        date_str = "the recorded date"
        status = "unknown"

    amount_str = f"{amount:.0f}" if isinstance(amount, (int, float)) else "the"
    cp_str = cp or "the recipient"

    try:
        return template.format(
            amount=amount_str,
            counterparty=cp_str,
            date=date_str,
            txn_id=txn_id,
            status=status,
            ref_id=ref_id,
        )
    except (KeyError, IndexError):
        return _FALLBACK_BN.format(ref_id=ref_id) if is_bn else _FALLBACK_EN.format(ref_id=ref_id)


def build_agent_summary(
    *,
    language: str,
    decision,
    ref_id: str,
) -> str:
    summary_template = _AGENT_SUMMARY_BN if language == "bn" else _AGENT_SUMMARY_EN
    reasons_str = ",".join(decision.reason_codes) if decision.reason_codes else "none"
    return summary_template.format(
        ref_id=ref_id,
        case_type=decision.case_type,
        severity=decision.severity,
        department=decision.department,
        evidence_verdict=decision.evidence_verdict,
        human_review_required=str(decision.human_review_required).lower(),
        confidence=decision.confidence,
        reasons=reasons_str,
    )


def build_recommended_next_action(
    *,
    language: str,
    decision,
) -> str:
    table = _NEXT_ACTION_BN if language == "bn" else _NEXT_ACTION_EN
    template = table.get(decision.case_type, table["other"])
    txn_id = decision.relevant_transaction_id or "N/A"
    return template.format(txn_id=txn_id)


def build_llm_prompt(
    *,
    complaint: str,
    decision,
    ref_id: str,
    language: str,
    matched_txn: Optional[object] = None,
) -> str:
    txn_id = decision.relevant_transaction_id or "N/A"
    reasons_str = ",".join(decision.reason_codes) if decision.reason_codes else "none"

    txn_block = "N/A"
    if matched_txn is not None:
        amount = getattr(matched_txn, "amount", "?")
        cp = getattr(matched_txn, "counterparty", "?")
        date_str = _format_date(getattr(matched_txn, "timestamp", None))
        status = getattr(matched_txn, "status", "?")
        txn_block = (
            f"transaction_id={txn_id}\n"
            f"amount={amount} BDT\n"
            f"counterparty={cp}\n"
            f"timestamp={date_str}\n"
            f"status={status}"
        )

    lang_note = "bn" if language == "bn" else "en"

    return (
        f"complaint_lang={lang_note}\n"
        f"case_type={decision.case_type}\n"
        f"severity={decision.severity}\n"
        f"department={decision.department}\n"
        f"evidence_verdict={decision.evidence_verdict}\n"
        f"human_review_required={str(decision.human_review_required).lower()}\n"
        f"reason_codes={reasons_str}\n"
        f"matched_transaction:\n{txn_block}\n"
        f"complaint:\n{complaint}\n"
        f"ref_id={ref_id}\n"
    )


def build_system_prompt(language: str) -> str:
    return _SYSTEM_PROMPT_BN if language == "bn" else _SYSTEM_PROMPT_EN