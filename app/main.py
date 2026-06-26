from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, List, Optional

from dotenv import load_dotenv

# Load .env from the repo root if present, so uvicorn picks up GOOGLE_API_KEY
# without requiring the user to export it manually.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"), override=False)

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.i18n import (
    build_agent_summary,
    build_customer_reply,
    build_llm_prompt,
    build_recommended_next_action,
    build_system_prompt,
)
from app.llm_client import LLMClient, LLMResult, new_client_from_env
from app.routing import RoutingDecision, decide
from app.safety import enforce_safety
from app.schemas import AnalyzeRequest, AnalyzeResponse, HealthResponse


logger = logging.getLogger("queuestorm")
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))


HARD_DEADLINE_SECONDS = float(os.environ.get("HARD_DEADLINE_SECONDS", "30"))
PARTIAL_THRESHOLD_SECONDS = float(os.environ.get("PARTIAL_THRESHOLD_SECONDS", "5"))


class AppState:
    llm: Optional[LLMClient] = None


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        state.llm = new_client_from_env()
        await state.llm.prewarm()
        logger.info("LLM client prewarmed: model=%s", state.llm.model)
    except Exception as exc:
        logger.warning("LLM prewarm failed, continuing without: %s", exc)
        state.llm = None
    yield
    state.llm = None


app = FastAPI(
    title="QueueStorm Investigator",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={
            "error": "invalid_request",
            "detail": exc.errors(),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code},
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


def _build_fallback_response(
    *,
    request: AnalyzeRequest,
    decision: RoutingDecision,
    language: str,
) -> AnalyzeResponse:
    ref_id = f"REF-{request.ticket_id}"
    return AnalyzeResponse(
        ticket_id=request.ticket_id,
        relevant_transaction_id=decision.relevant_transaction_id,
        evidence_verdict=decision.evidence_verdict,
        case_type=decision.case_type,
        severity=decision.severity,
        department=decision.department,
        agent_summary=build_agent_summary(language="en", decision=decision, ref_id=ref_id),
        recommended_next_action=build_recommended_next_action(
            language="en", decision=decision
        ),
        customer_reply=build_customer_reply(
            language=language,
            decision=decision,
            ref_id=ref_id,
            matched_txn=decision.matched_transaction,
        ),
        human_review_required=decision.human_review_required,
        confidence=decision.confidence,
        reason_codes=decision.reason_codes,
    )


async def _call_llm_with_timeout(
    llm: LLMClient,
    *,
    request: AnalyzeRequest,
    decision: RoutingDecision,
    language: str,
) -> LLMResult:
    ref_id = f"REF-{request.ticket_id}"
    system_prompt = build_system_prompt(language)
    user_prompt = build_llm_prompt(
        complaint=request.complaint,
        decision=decision,
        ref_id=ref_id,
        language=language,
        matched_txn=decision.matched_transaction,
    )
    full_prompt = f"{system_prompt}\n\n{user_prompt}"

    summary = _summarize_history(request.transaction_history or [])

    coro = llm.generate_reply(
        ticket_id=request.ticket_id,
        complaint=request.complaint,
        language=language,
        case_type_hint=decision.case_type,
        transaction_summary=summary,
    )
    try:
        return await asyncio.wait_for(coro, timeout=llm.timeout_seconds)
    except asyncio.TimeoutError:
        return LLMResult(ok=False, error="timeout", used_fallback=True)
    except Exception as exc:
        return LLMResult(ok=False, error=f"call_failed:{type(exc).__name__}", used_fallback=True)


def _summarize_history(history: List[Any]) -> str:
    if not history:
        return "[]"
    out: List[str] = []
    for t in history[:5]:
        tid = getattr(t, "transaction_id", "?")
        amt = getattr(t, "amount", 0)
        st = getattr(t, "status", "?")
        out.append(f"{tid}:{amt}BDT:{st}")
    return " | ".join(out)


@app.post("/analyze-ticket", response_model=AnalyzeResponse)
async def analyze_ticket(request: AnalyzeRequest) -> AnalyzeResponse:
    loop = asyncio.get_event_loop()
    deadline = loop.time() + HARD_DEADLINE_SECONDS
    language = request.language or "en"

    decision = decide(request)

    ref_id = f"REF-{request.ticket_id}"

    base_response = _build_fallback_response(
        request=request,
        decision=decision,
        language=language,
    )

    if not decision.needs_llm and not decision.needs_llm_enrichment:
        return base_response

    if state.llm is None:
        logger.info("LLM unavailable for ticket %s, returning deterministic", request.ticket_id)
        return base_response

    remaining = deadline - loop.time()
    if remaining <= 0:
        return base_response

    result = await _call_llm_with_timeout(
        state.llm,
        request=request,
        decision=decision,
        language=language,
    )

    if not result.ok or not result.data:
        return base_response

    data = result.data
    raw_reply = data.get("customer_reply", "") or base_response.customer_reply
    raw_summary = data.get("agent_summary", "") or base_response.agent_summary
    raw_action = data.get("recommended_next_action", "") or base_response.recommended_next_action

    safety = enforce_safety(raw_reply, request.complaint, language=language)

    customer_reply = safety.cleaned_text if safety.safe else base_response.customer_reply
    extra_reasons: List[str] = list(safety.triggered_rules or [])
    if safety.injection_detected:
        extra_reasons.append("injection_detected")

    return AnalyzeResponse(
        ticket_id=request.ticket_id,
        relevant_transaction_id=decision.relevant_transaction_id,
        evidence_verdict=decision.evidence_verdict,
        case_type=decision.case_type,
        severity=decision.severity,
        department=decision.department,
        agent_summary=raw_summary if raw_summary else base_response.agent_summary,
        recommended_next_action=raw_action if raw_action else base_response.recommended_next_action,
        customer_reply=customer_reply,
        human_review_required=decision.human_review_required or not safety.safe,
        confidence=decision.confidence,
        reason_codes=decision.reason_codes + extra_reasons,
    )