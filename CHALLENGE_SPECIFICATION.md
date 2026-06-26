# TECHNICAL SPECIFICATION: QUEUESTORM INVESTIGATOR
## Event: SUST CSE Carnival 2026 · Codex Community Hackathon · Online Preliminary
## Sponsor/Context: bKash presents SUST CSE Carnival 2026 in association with Codex & Poridhi.io

---

## 1. ARCHITECTURAL OBJECTIVE
You are building an internal Copilot API for fintech digital finance support operations under extreme load conditions. The system reads individual customer tickets containing unstructured narratives alongside raw transaction history arrays. It performs programmatic telemetry lookup, evaluates compliance, overrides prompt injections, maps categorical metadata, tracks severity levels, and drafts safe customer responses.

### Critical Runtime Performance Enforcements
- **GET /health Readiness:** Must respond with `{"status": "ok"}` within 60 seconds of container engine initialization.
- **POST /analyze-ticket Latency Tiers:** * Full latency score credit: Response generated in <= 5 seconds.
  * Partial credit: 5 to 15 seconds.
  * Timeout failure dropoff: > 30 seconds (treated as an absolute failure).
- **Service Resilience:** High-volume automated traffic tests will trigger malformed JSON payloads and empty text fields. The service must handle these gracefully using strict standard HTTP status responses without crashing or exiting.

---

## 2. EXACT SCHEMA CONTRACTS

### 2.1 Request Schema (`POST /analyze-ticket`)
The incoming JSON body will enforce the following field configuration:

| Field Name | Data Type | Required? | Accepted Values / Enum Bounds |
| :--- | :--- | :--- | :--- |
| `ticket_id` | String | **YES** | Unique alphanumeric ID string. |
| `complaint` | String | **YES** | Raw text statement (English, Bangla, or mixed Banglish). |
| `language` | String Enum | Optional | `en`, `bn`, `mixed` |
| `channel` | String Enum | Optional | `in_app_chat`, `call_center`, `email`, `merchant_portal`, `field_agent` |
| `user_type` | String Enum | Optional | `customer`, `merchant`, `agent`, `unknown` |
| `campaign_context`| String | Optional | Arbitrary text campaign identifiers. |
| `transaction_history`| Array (Objects)| Optional | List of recent transaction structures (0 to 5 entries). |
| `metadata` | Object | Optional | Embedded contextual validation details. |

#### Nested Transaction History Structure
Each object inside the `transaction_history` array contains:
- `transaction_id` (String, Required)
- `timestamp` (String ISO 8601, Required)
- `type` (String Enum, Required): `transfer`, `payment`, `cash_in`, `cash_out`, `settlement`, `refund`
- `status` (String Enum, Required): `completed`, `failed`, `pending`, `reversed`
- `amount` (Number, Required): Total monetary volume in BDT.
- `counterparty` (String, Required): Target phone number, merchant ID, or agent ID node.

### 2.2 Response Schema (`POST /analyze-ticket`)
The outgoing response payload must strictly match the following dictionary structure. Any variant casing, missing properties, or spelling alterations will trigger a hard automated schema validation failure.

| Response Key | Data Type | Required? | Operational Content Definitions |
| :--- | :--- | :--- | :--- |
| `ticket_id` | String | **YES** | Must perfectly echo the incoming `ticket_id`. |
| `relevant_transaction_id`| String / Null | **YES** | The matching token ID from history, or `null` if unverified. |
| `evidence_verdict` | String Enum | **YES** | `consistent`, `inconsistent`, `insufficient_data` |
| `case_type` | String Enum | **YES** | Core categorical taxonomy classification match. |
| `severity` | String Enum | **YES** | `low`, `medium`, `high`, `critical` |
| `department` | String Enum | **YES** | Operational resolution group targeting. |
| `agent_summary` | String | **YES** | 1 to 2 concise English summary sentences for the agent queue. |
| `recommended_next_action`| String | **YES** | Operational instruction guide for the responding human agent. |
| `customer_reply` | String | **YES** | Sanitized message sent to the end user. |
| `human_review_required` | Boolean | **YES** | `true` if ambiguous, safety-critical, high-value, or contested. |
| `confidence` | Float | Optional | Reliability score decimal between `0.0` and `1.0`. |
| `reason_codes` | Array (Strings)| Optional | Traceability lookup labels explaining core routing choices. |

---

## 3. CORE ROUTING & TAXONOMY LOOKUP MATRIX

The agent must route cases using the exact logical bindings listed in the table below:

| Classified Case Type (`case_type`) | Target Processing Department (`department`) | Standard Severity Weighting (`severity`) | Manual Escalation Trigger (`human_review_required`) |
| :--- | :--- | :--- | :--- |
| `wrong_transfer` | `dispute_resolution` | `high` (if transaction match is found) | `true` |
| `payment_failed` | `payments_ops` | `high` | `false` (or `true` if ledger mismatch occurs) |
| `refund_request` | `customer_support` | `low` (promoted to `high` if contested, see §3.1) | `false` (promoted to `true` if contested, see §3.1) |
| `duplicate_payment` | `payments_ops` | `high` | `true` |
| `merchant_settlement_delay`| `merchant_operations` | `medium` | `false` |
| `agent_cash_in_issue` | `agent_operations` | `high` | `true` |
| `phishing_or_social_engineering`| `fraud_risk` | `critical` | `true` |
| `other` | `customer_support` | `low` | `false` |

### 3.1 Routing Footnotes & Escalation Rules

The conditional severity / escalation cells above are resolved by the following deterministic rules, evaluated in order:

1. **`insufficient_data` evidence ⇒ escalation.** When `evidence_verdict == "insufficient_data"`, force `human_review_required = true` and cap `confidence ≤ 0.5`, regardless of `case_type`.
2. **`critical` severity ⇒ escalation.** When `severity == "critical"` (i.e. `phishing_or_social_engineering` matched), `human_review_required = true` is already implied by §3; do not override.
3. **`wrong_transfer` no-match branch.** When no `transaction_history` entry can be matched against the complaint text, downgrade `severity` to `medium`, set `relevant_transaction_id = null`, and keep `human_review_required = true` (ambiguous evidence rule applies).
4. **`refund_request` contested promotion.** A `refund_request` is "contested" when the `transaction_history` contains a matching entry with `status ∈ {"completed", "reversed"}` AND the complaint explicitly disputes that resolution (keywords: `already refunded`, `not received`, `didn't get`, `still waiting`, `double charged`). Contested ⇒ `severity = "high"` and `human_review_required = true`. Otherwise the defaults from the §3 row apply.
5. **`payment_failed` ledger mismatch promotion.** Promote `human_review_required` to `true` when `payment_failed` is detected AND `evidence_verdict == "inconsistent"` (e.g. customer claims failure but history shows `completed`).
6. **`high-value` heuristic.** Any matched `transaction_history` entry with `amount ≥ 50000` BDT forces `human_review_required = true` regardless of `case_type` (overrides any `false` from the matrix).

---

## 4. RESPONSE QUALITY & SAFETY CONTRACTS

### 4.1 `customer_reply` Safety Guardrails

The `customer_reply` string MUST satisfy all three rules simultaneously. Violations are tracked in `reason_codes` for traceability:

- **Credential filter:** Must never request a PIN, OTP, password, access token, full card number, or CVV.
- **Financial commitment filter:** Must never use definitive completion phrasing such as `"We have reversed"`, `"Your money has been refunded"`, `"We will unlock your profile"`. Mandated compliant phrasing: `"Any eligible amount will be returned through official channels after review"`, `"The operational division will cross-reference this ledger sequence"`.
- **Third-party contact filter:** Must never direct the user to contact the agent, a phone number, an email address, a social media handle, or any channel outside the official in-app support surface.

### 4.2 Language Mirroring

- If the resolved language is `bn` (Bangla), the `customer_reply` MUST be written entirely in native Bangla script.
- If `en` or `mixed`, the `customer_reply` MUST be written in plain English.
- All triage metadata (`agent_summary`, `recommended_next_action`, `reason_codes`) MUST always be English, regardless of input language.

### 4.3 `confidence` Heuristic (Optional Field)

`confidence` is always emitted (not omitted) and is derived as: `consistent → 0.9`, `inconsistent → 0.85`, `insufficient_data → 0.5`. Override downward by `0.2` whenever prompt-injection patterns are detected in the complaint text.

### 4.4 `reason_codes` Closed Enum

`reason_codes` MUST be a subset of the following closed list. Any code outside this list triggers a schema validation failure. The list is derived from the problem-statement PDF Section 7.1 example (`transaction_match`) plus the routing and safety rules in Sections 3 and 4 of this document:

```
wrong_transfer, payment_failed, refund_request, duplicate_payment,
merchant_settlement_delay, agent_cash_in_issue, phishing_attempt,
social_engineering, no_match, ambiguous_evidence, amount_mismatch,
status_mismatch, counterparty_mismatch, prompt_injection_detected,
credential_request_blocked, third_party_contact_blocked,
financial_commitment_blocked, high_value_escalation,
transaction_match, counterparty_unverified, suspicious_pattern,
duplicate_charge_detected, settlement_window_exceeded,
agent_cash_not_reflected
```

---

## 5. ENDPOINT CONTRACTS

### 5.1 `GET /health`

- **Latency contract:** Must return a 200 OK within 60 seconds of container start.
- **Body (literal):** `{"status": "ok"}`
- **Behavior:** Pure liveness probe; no dependency checks. Always returns 200 unless the process is unrecoverable.

### 5.2 `POST /analyze-ticket`

- **Request body:** Section 2.1.
- **Response body:** Section 2.2.
- **Latency tiers:** ≤ 5s full credit, 5–15s partial credit, > 30s hard failure.
- **Error status matrix:**
  - `400 Bad Request` — JSON parse failure or missing required fields (`ticket_id`, `complaint`).
  - `422 Unprocessable Entity` — Body parses, but `complaint` is empty or whitespace-only.
  - `500 Internal Server Error` — Internal failure; body MUST NOT include stack traces, internal property names, or active credentials.

---

## 6. DEPLOYMENT CONTRACT

- **Container port:** 8000 (overridable via `PORT` env var per the bundled `Dockerfile`).
- **Process model:** Single uvicorn worker is sufficient for the harness load profile. No auth on `/health` or `/analyze-ticket`.
- **Python runtime:** 3.11 (per `Dockerfile`).
- **Mandatory dependencies (from `requirements.txt`):** `fastapi`, `uvicorn`, `pydantic`. The remaining entries (`httpx`, `pytest`, `python-dotenv`, `google-genai`, `requests`) are optional tooling.
- **Resource envelope (per PDF §9):** Target 2 vCPU / 4 GB RAM. No GPU. Image size preference is < 5 GB; pull large model assets at runtime rather than baking them in.
- **Allowed external services (per PDF §9.1):** Google AI (`google-genai`), OpenAI, Anthropic, Hugging Face Inference, Cohere, or any comparable major LLM provider. Outbound calls to personal infrastructure or unrelated endpoints may be blocked.
- **Secret handling (per PDF §9.2):** API keys are read from environment variables only. Never committed to the repo. Responses, logs, and error bodies must not leak secrets, tokens, or stack traces.
- **Latency contract (per PDF §9):** `POST /analyze-ticket` MUST respond within 30 seconds. `GET /health` MUST return `{"status":"ok"}` within 60 seconds of service start.