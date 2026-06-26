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
- `status` (String Enum, Required): `completed`, `6failed`, `pending`, `reversed`
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
| `refund_request` | `customer_resolution` / `customer_support` | `low` (standard) / `high` (if contested) | Dependent on dispute tracking state |
| `duplicate_payment` | `payments_ops` | `high` | `true` |
| `merchant_settlement_delay`| `merchant_operations` | `medium` | `false` |
| `agent_cash_in_issue` | `agent_operations` | `high` | `true` |
| `phishing_or_social_engineering`| `fraud_risk` | `critical` | `true` |
| `other` | `customer_support` | `low` | `false` |