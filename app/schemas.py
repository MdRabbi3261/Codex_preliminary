from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


Language = Literal["en", "bn", "mixed"]
Channel = Literal[
    "in_app_chat", "call_center", "email", "merchant_portal", "field_agent"
]
UserType = Literal["customer", "merchant", "agent", "unknown"]
TxnType = Literal[
    "transfer", "payment", "cash_in", "cash_out", "settlement", "refund"
]
TxnStatus = Literal["completed", "failed", "pending", "reversed"]

EvidenceVerdict = Literal["consistent", "inconsistent", "insufficient_data"]
Severity = Literal["low", "medium", "high", "critical"]

ReasonCode = Literal[
    "wrong_transfer",
    "payment_failed",
    "refund_request",
    "duplicate_payment",
    "merchant_settlement_delay",
    "agent_cash_in_issue",
    "phishing_attempt",
    "social_engineering",
    "no_match",
    "ambiguous_evidence",
    "amount_mismatch",
    "status_mismatch",
    "counterparty_mismatch",
    "prompt_injection_detected",
    "credential_request_blocked",
    "third_party_contact_blocked",
    "financial_commitment_blocked",
    "high_value_escalation",
]

CaseType = Literal[
    "wrong_transfer",
    "payment_failed",
    "refund_request",
    "duplicate_payment",
    "merchant_settlement_delay",
    "agent_cash_in_issue",
    "phishing_or_social_engineering",
    "other",
]

Department = Literal[
    "dispute_resolution",
    "payments_ops",
    "customer_resolution",
    "customer_support",
    "merchant_operations",
    "agent_operations",
    "fraud_risk",
]


class Transaction(BaseModel):
    transaction_id: str = Field(..., min_length=1)
    timestamp: str = Field(..., min_length=1)
    type: TxnType
    status: TxnStatus
    amount: float = Field(..., ge=0)
    counterparty: str = Field(..., min_length=1)


class AnalyzeRequest(BaseModel):
    ticket_id: str = Field(..., min_length=1)
    complaint: str = Field(..., min_length=1)
    language: Optional[Language] = None
    channel: Optional[Channel] = None
    user_type: Optional[UserType] = None
    campaign_context: Optional[str] = None
    transaction_history: Optional[List[Transaction]] = None
    metadata: Optional[dict] = None

    @field_validator("complaint")
    @classmethod
    def _strip_complaint(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("complaint must be non-empty")
        return v


class AnalyzeResponse(BaseModel):
    ticket_id: str
    relevant_transaction_id: Optional[str] = None
    evidence_verdict: EvidenceVerdict
    case_type: CaseType
    severity: Severity
    department: Department
    agent_summary: str
    recommended_next_action: str
    customer_reply: str
    human_review_required: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason_codes: List[ReasonCode] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"