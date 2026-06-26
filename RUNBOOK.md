# QueueStorm Investigator — RUNBOOK

Step-by-step instructions for a judge or teammate to bring up the service from a clean clone. No inference. No guessing. Every command is copy-pasteable.

## 0. Prerequisites

- Docker Engine 24+ (or Python 3.11 if running locally without Docker)
- 2 vCPU / 4 GB RAM available
- Outbound HTTPS allowed to `generativelanguage.googleapis.com` (or whichever LLM provider you configure)
- An API key for the chosen LLM provider, supplied via environment variable (e.g. `your-google-ai-studio-key-here`)

## 1. Clone

```bash
git clone https://github.com/MdRabbi3261/Codex_preliminary.git
cd Codex_preliminary
```

## 2. Configure secrets

Create a local `.env` file (do not commit it):

```bash
cp .env.example .env
```

Edit `.env` and fill in real values. The minimum is:

```
your-google-ai-studio-key-here=your-real-key-here
PORT=8000
```

## 3. Run with Docker (recommended)

```bash
docker build -t queuestorm-investigator:latest .
docker run --rm -p 8000:8000 --env-file .env queuestorm-investigator:latest
```

The container listens on `0.0.0.0:8000`. The `PORT` env var overrides the internal uvicorn port.

## 4. Run locally without Docker

```bash
python -m venv .venv
source .venv/bin/activate   # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
export your-google-ai-studio-key-here=your-real-key-here
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 5. Smoke test

Wait until both endpoints respond. The first call may be slow while the model client warms up.

```bash
curl -s http://localhost:8000/health
# expected: {"status":"ok"}

curl -s -X POST http://localhost:8000/analyze-ticket \
  -H "Content-Type: application/json" \
  -d @sample_input.json
```

A full worked `sample_input.json` plus its expected `sample_output.json` are committed in `samples/`.

## 6. Run the test suite

```bash
pytest -q
```

## 7. Submission paths (per PDF §10)

The service is eligible for any one of these submission forms. Provide at least one:

- **A. Live URL** — point the organizer at `https://your-host/health` and `/analyze-ticket`.
- **B. Docker image** — `docker pull <username>/<image>:<tag>` plus the run command from §3.
- **C. Code + this runbook** — judges clone the repo and follow §1–§5 above.

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `/health` returns 500 | Process crashed during lifespan pre-warm | Check container logs; missing `your-google-ai-studio-key-here` is the most common cause |
| `analyze-ticket` returns `insufficient_data` for every request | LLM call is failing / timing out | Verify outbound HTTPS; check the model name is one of the allowed flash-class models |
| `customer_reply` looks English-only on Bangla input | Language detector defaulted to `en` | Inspect `reason_codes` for `prompt_injection_detected`; ensure complaint contains Bangla script characters (`\u0980`–`\u09FF`) |
| Service responds > 5s on first call | Cold-start model client handshake | The `lifespan` pre-warm should mitigate this; if it persists, raise the LLM `timeout` in `app/llm_client.py` |
| `reason_codes` validation fails | A code outside the closed enum was emitted | See `CHALLENGE_SPECIFICATION.md` §4.4 for the allowed list |

## 9. Environment variables

| Name | Required? | Default | Purpose |
| --- | --- | --- | --- |
| `your-google-ai-studio-key-here` | Yes (if using Google AI) | — | API key for the LLM provider |
| `PORT` | No | `8000` | HTTP listen port |
| `LLM_TIMEOUT_SECONDS` | No | `2.5` | Hard timeout per LLM call |
| `LLM_MAX_CONCURRENCY` | No | `8` | Maximum in-flight LLM calls |
| `HIGH_VALUE_BDT_THRESHOLD` | No | `50000` | Threshold above which `human_review_required = true` is forced |

## 10. Resource envelope

Per PDF §9: target 2 vCPU / 4 GB RAM, no GPU, image < 5 GB. The bundled `Dockerfile` uses `python:3.11-slim` and installs only the mandatory dependencies, leaving several GB of headroom.
