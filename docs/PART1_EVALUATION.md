# Part 1 evaluation and monitoring

The `/observability` page shows the signed-in account's traces, provider usage,
stage timings and evaluation scores. Its MongoDB records work without Langfuse.
It is account-scoped, not a cross-customer administrator console.

## Configure

Place these in `backend/.env` (placeholders already added). Restart the web process
and any separate worker after changing them. Never use VITE_ variables for keys.

```dotenv
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_BASE_URL=https://cloud.langfuse.com
LANGFUSE_DASHBOARD_URL=
```

Use the base URL for your Langfuse region or self-hosted deployment; the optional
dashboard URL is a project link. These are different URLs. The server appends
`/api/public/otel/v1/traces` for OTLP traces and `/api/public/ingestion` for scores.
An optional generic collector can be set through `OTEL_EXPORTER_OTLP_ENDPOINT`
(base URL), `OTEL_EXPORTER_OTLP_HEADERS`, and
`OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` (full metrics URL). Do not point the metrics
exporter at Langfuse; its OTLP endpoint accepts traces. You do not need a separate
collector for local monitoring or Langfuse tracing.

References: [Langfuse OTLP](https://langfuse.com/integrations/native/opentelemetry),
[score ingestion](https://langfuse.com/docs/evaluation/evaluation-methods/scores-via-sdk).

## What is measured

| Stage | Check | Meaning |
|---|---|---|
| OCR verification | Extraction and running-balance consistency | Existing Decimal rules agree; not proof of source accuracy |
| Categorization | Financial fields preserved | Category assignment did not alter or drop money/date/balance rows |
| MongoDB | Read-back exact match | IDs, tenant, date, category and Decimal amounts match expected records |
| Insights | Nonempty list of strings | Contract check only; factual correctness remains unmeasured |
| Vector DB | Read-back IDs and metadata | Stored vectors belong to the expected transactions and tenant |
| Worker | Required stages completed | Transactions, insights and verified vector records completed |
| Offline benchmark | Financial exact match, precision, recall | Output compared with manually reviewed source rows |
| Offline categories | Macro-F1 and label coverage | Categories compared with reviewer labels on unambiguous matched rows |

Unmeasured scores remain `null` and never count as passes or failures. The online
pass percentage describes checks, not overall OCR accuracy. Category matching
excludes ambiguous repeated financial keys and reports that coverage separately.
The existing categorization methodology has not changed.

## Trace flow and storage

HTTP upload → individual LangGraph stage spans → Mongo read-back → durable job
with W3C trace context → worker attempt span → insights → vector read-back.
The worker creates its own Mongo trace linked through `parent_trace_id`, while
sharing the OpenTelemetry trace ID. Retries remain individually inspectable.
HTTP success means the request returned; the worker trace and upload status
determine completion of enrichment.

Telemetry captures counts, scores, timings and model usage. It excludes PDFs,
passwords, prompts, raw provider error messages and transaction descriptions.
Langfuse keys remain server-side. Local scores persist even if remote delivery
fails; `score_export_status` reports disabled/exported/failed. OTLP uses a bounded
in-memory batch queue, not a durable audit log. Score IDs support safe replay.
For audit-grade external delivery, add a durable outbox/collector queue and
retention/access policies before launch.

## Run regression checks

From `backend`, use the project lockfile (plain `uv pip install -e .` can resolve
incompatible newer LangChain versions):

```powershell
uv sync --locked
uv run --locked pytest -q tests
uv run --locked python -m experiments.evaluate_part1 --dataset tests/fixtures/part1_synthetic.json
```

If the existing Windows `.venv` is locked/broken, use an isolated environment:
`$env:UV_PROJECT_ENVIRONMENT='.venv2'` before `uv sync --locked`.

The committed synthetic fixture verifies the evaluator; it is not a bank accuracy
benchmark. Store real reviewed fixtures in ignored `backend/evaluation-private/`.
Each case contains `id`, `bank`, `expected`, and `actual` row arrays. Fields:
ISO `date`, decimal-string `debit`, `credit`, optional `balance` (same evidence
contract on both sides), and optional reviewer `category`. Use one dataset per
bank/template or run each subset separately. Preserve duplicate source rows.
Do not use the OCR's own output as the expected answer.

`evaluate_part1` evaluates saved candidate outputs; it does not call OCR or LLMs.
Use the existing extraction experiments to generate candidates, review the PDF
independently, then pair the output with expected rows. Reports contain scores,
hashed case IDs, a dataset content hash, and evaluator version; no transaction rows.
An optional `--publish-user-id <existing-test-user-id>` records the run in MongoDB
and sends numeric scores to configured Langfuse. Publishing must target a dedicated
account you control. Failed measured checks return exit code 1 for CI.

## Verification boundary

The local integration tests use an in-memory MongoDB and provider/vector doubles.
They verify idempotence, worker correlation, schema and storage checks, score
delivery failures, and tenant isolation. A browser fixture server is available at
`python -m experiments.serve_monitoring_demo` with `MONGO_MOCK=true` and blank
Langfuse keys; it serves synthetic data only and binds to localhost:8097.
Point a local frontend at that port and run it on 3017 for browser verification.
Never deploy that demo module.

Real statement accuracy requires a manually reviewed bank dataset. Live Langfuse
delivery, live Pinecone consistency and production load need separately verified
credentials and infrastructure; synthetic checks do not establish those claims.

Local verification on 2026-09-20: frontend lint/build passed; the complete backend
suite passed, including synthetic lifecycle, tenant isolation and vector-failure
retry checks. A real browser signed in to the local fixture server, opened the
Observability page, inspected the pass/fail/unmeasured results, and changed its
time window. A fixture with one pass, one failure and one unmeasured check showed
50%, excluding the unmeasured check. No live financial data or remote Langfuse
delivery was used in that verification.
