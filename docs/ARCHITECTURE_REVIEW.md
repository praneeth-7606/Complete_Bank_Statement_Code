# Financial Statement Analyzer — Architecture Review

## Scope and current flow

The frontend is a Vite/React single-page application. The FastAPI backend owns authentication, statement ingestion, OCR, transaction persistence, analytics, chat/RAG, and investment-related routes. MongoDB is the system of record; Pinecone stores transaction embeddings. Hosted model routing is intended to be Gemini first with Groq fallback, while OCR is Mistral first with Gemini vision fallback.

The intended user journey is:

```text
browser → auth → PDF upload → validation → background processing
        → OCR/extraction → normalization/categorization → MongoDB/Pinecone
        → dashboard/analytics/transactions → correction → chat/RAG
```

## E2E coverage and evidence

`backend/e2e_agent.py` contains the LangChain browser agent and records step status, latency, screenshots, provider bootstrap errors, and usage metrics. Its scenarios are public authentication, protected routes, dashboard/analytics, upload and processing, transaction filters/corrections, chat/RAG, and logout. `--smoke-only` runs deterministic browser checks without an LLM; full mode adds authenticated, data-dependent workflows.

The browser layer has been verified locally for login rendering, signup navigation, protected-route redirection, and clean browser console logs. Full authenticated execution is gated by a dedicated test account, a redacted PDF fixture, MongoDB, and valid hosted-provider credentials.

## Production risks and required changes

| Area | Current risk | Required hardening |
| --- | --- | --- |
| Job processing | In-process background tasks are lost on restart and may duplicate work | Use a durable queue/worker or MongoDB claim loop with leases, retries, dead-letter state, and idempotency keys |
| Financial precision | Float arithmetic can create incorrect totals | Store money as integer minor units or `Decimal`; validate currency and rounding at API boundaries |
| Idempotency | Retries can duplicate uploads, transactions, embeddings, or corrections | Use request/idempotency keys and unique constraints on `(user_id, statement_hash, transaction_fingerprint)` |
| Provider routing | A bad key/quota/timeout can stop the workflow; free-provider limits are variable | Add bounded timeouts, jittered retries, circuit breakers, provider health state, fallback reason, and quota-aware routing |
| Authentication | Multi-worker deployments must share session/refresh state | Use a shared session store, token rotation/revocation, secure cookies, CSRF protection where applicable, and strict CORS origins |
| Authorization | Every statement, transaction, chat, and log query must remain user-scoped | Add negative authorization tests for every resource endpoint and enforce ownership in the data layer |
| Sensitive data | Bank PDFs and account data are high-impact personal data | Malware/content scanning, encryption at rest, redaction before model calls, retention/deletion policy, audit events, and no secret/PII logging |
| Vector search | Changing embedding model/dimension silently invalidates retrieval quality | Version embeddings, keep model metadata, reindex through a controlled migration, and evaluate retrieval quality |
| Frontend delivery | Production bundle is about 1 MB and legacy lint debt remains | Route-level lazy loading, chunk analysis, remove unused code incrementally, and treat lint errors as CI failures |
| Operability | In-memory history and ad-hoc logs do not support ten concurrent users reliably | Shared state, structured logs, correlation IDs, metrics, traces, dashboards, and alert thresholds |

## Observability contract

Every request should carry a `request_id` and authenticated `user_id` (hashed/pseudonymized in telemetry). Emit structured events for:

- request start/end, status, route, latency, payload size, and error class;
- upload hash, page count, queue wait, processing duration, and final state;
- OCR/provider name, model, latency, retry count, fallback reason, and sanitized error;
- LLM input/output tokens, estimated cost, model, cache hit, tool calls, and trace ID;
- categorization confidence, validation failures, correction events, and vector-search latency.

Do not log passwords, PDF passwords, account numbers, raw statements, full prompts, or model responses containing sensitive transaction data. Use redacted samples and retention limits. LangSmith can provide agent traces; OpenTelemetry-compatible metrics/traces should cover the FastAPI, worker, MongoDB, Pinecone, and provider boundaries.

## Release gates

Before production traffic:

1. Run unit, API authorization, parser/OCR fixture, provider-failure, idempotency, and worker-restart tests.
2. Run `e2e_agent.py --smoke-only` on every deployment preview.
3. Run full E2E against a seeded isolated environment with a dedicated test account and redacted fixtures.
4. Verify no cross-user reads, duplicate processing, float drift, secret leakage, or unbounded retries.
5. Load-test at the expected concurrency and verify queue age, p95 latency, error rate, provider fallback rate, and cost budgets.

The current implementation is suitable as an E2E foundation, but it should not be considered production-ready until the durable worker, decimal money model, idempotency, shared state, and telemetry contract are implemented and tested.
