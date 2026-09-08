# Financial Statement Analyzer

An AI-powered financial workspace that converts bank-statement PDFs into searchable, categorized transactions and actionable insights. It contains a React/Vite frontend and a FastAPI/MongoDB backend.

## Features

- Email/password authentication and optional Google OAuth.
- Single and batch PDF uploads, including protected PDFs.
- File type, size, page-count, ownership, and duplicate-hash validation.
- Multi-bank statement extraction, transaction normalization, balance verification, and decimal-safe totals.
- Rule-based, merchant-based, correction-history, and AI transaction categorization.
- Dashboards for balances, income, expenses, categories, trends, and recent transactions.
- Filtering, category corrections, statement details, deletion, and live processing logs.
- Natural-language chat using MongoDB filters, Pinecone semantic search, reranking, aggregation, and RAG.
- Financial insights, anomaly detection, and optional Groww investment assistance.

## End-to-end workflow

```text
Sign up / log in
      ↓
Upload PDF with bearer token
      ↓
Validate file, limits, ownership, and duplicate hash
      ↓
Mistral OCR extracts text and tables
      ↓ (if OCR fails or output is invalid)
Gemini Vision extracts the statement as fallback
      ↓
Normalize dates, debits, credits, balances, and descriptions
      ↓
Rules + merchant patterns + correction history classify transactions
      ↓ (for unresolved batches)
Gemini Flash categorizes; Groq GPT-OSS-20B is the text-call fallback
      ↓
Calculate decimal-safe totals and verify balances
      ↓
Save upload, job, and transactions in MongoDB
      ↓
Generate embeddings and index transactions in Pinecone
      ↓
Serve dashboard, analytics, insights, and authenticated chat
```

## Hosted AI provider order

The project uses hosted APIs and does not require local LLMs:

1. **Mistral OCR** — primary PDF OCR and table extraction.
2. **Gemini Flash** — vision fallback, structuring, categorization, insights, RAG planning, and chat.
3. **Groq GPT-OSS-20B** — automatic Gemini fallback for text and tool-calling workloads through Groq's OpenAI-compatible API.

Only providers with configured keys are enabled. Structured responses are validated before persistence. If all AI providers fail, deterministic processing continues where possible and unresolved categories are marked accordingly.

## Architecture

### Frontend

React 18, Vite, React Router, Axios bearer-token client, Recharts, Tailwind CSS, reusable layouts, dashboard components, upload screens, analytics, transaction management, chat, and investment views.

### Backend

FastAPI REST API, MongoDB with Beanie/Motor, Mistral SDK, Google/LangChain integrations, LangGraph workflows, Pinecone vector search, user-scoped resources, processing-job metadata, and optional Groww API/MCP integrations.

## Repository structure

```text
backend/app/main.py                    FastAPI app and REST routes
backend/app/smart_extractor.py         PDF validation, OCR, parsing, processing
backend/app/llm_provider.py            Gemini-first/Groq-fallback router
backend/app/agent_categorization.py    Rules, merchants, history, and AI categories
backend/app/agent_analyst.py           Financial insights and anomalies
backend/app/agentic_rag.py             Query planning, retrieval, reranking, answers
backend/app/vector_store_pinecone.py  Embeddings and Pinecone integration
backend/app/models.py                  MongoDB/Beanie models
backend/app/config.py                  Environment and startup validation
backend/tests/                         Backend unit tests
frontend/src/pages/                    Product screens
frontend/src/components/               Reusable UI components
frontend/src/services/api.js           Frontend API client
```

## Prerequisites

- Python 3.11+.
- Node.js 18+ and npm.
- MongoDB, local or hosted.
- Mistral and Gemini API keys.
- Groq API key for Gemini text-call failover.
- Pinecone API key and index for semantic RAG.

## Environment configuration

Copy `backend/.env.example` to `backend/.env` and fill in the secrets:

```env
MONGO_URI=mongodb://localhost:27017/financial
SECRET_KEY=use-a-random-secret-at-least-32-characters-long
MISTRAL_API_KEY=your_mistral_key
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
GEMINI_MODEL=gemini-2.5-flash
GROQ_MODEL=openai/gpt-oss-20b
GROQ_BASE_URL=https://api.groq.com/openai/v1
PINECONE_API_KEY=your_pinecone_key
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=financial-transactions
```

Google OAuth, encryption, Groww credentials, upload limits, and other optional settings are documented in `backend/.env.example`. Never commit `backend/.env`, expose keys in frontend code, or print secrets in logs.

## Run locally

From `backend/`:

```powershell
uv sync
uv run uvicorn app.main:app --reload --port 8080
```

From `frontend/` in a second terminal:

```powershell
npm install
npm run dev
```

The frontend normally runs at `http://localhost:5173` and the API at `http://localhost:8080`. Set the frontend API URL in `frontend/.env` when the backend is hosted elsewhere.

## Main API routes

Authentication: `POST /signup`, `POST /login`, `POST /google`, `POST /refresh`, `GET /me`, `POST /logout`.

Statements: `POST /process-statement/`, `POST /process-multiple-statements/`, `GET /statements/`, `GET /statement/{upload_id}`, `GET /background-status/{upload_id}`, `DELETE /statement/{upload_id}`, `GET /stream-logs/{upload_id}`.

Transactions and analytics: `GET /api/transactions/filtered`, `PUT /api/transactions/{transaction_id}/category`, `POST /correct-transaction/`, `GET /api/dashboard/stats`, `GET /api/analytics/by-category`, `GET /api/analytics/by-date`.

AI: `POST /chat`. Optional investment routes are mounted under the investment router for chat, history clearing, and memory statistics.

All statement, transaction, analytics, chat, and log operations must be scoped to the authenticated user.

## Verification

```powershell
# Backend
cd backend
uv run python -m compileall -q app tests
uv run pytest -q tests

# Frontend
cd ../frontend
npm run lint
npm run build
```

Full API verification requires MongoDB and valid provider credentials. Expand coverage with authenticated API tests, OCR fixtures, provider-failure simulations, duplicate uploads, authorization-isolation tests, and upload-to-chat end-to-end tests.

## Production checklist

- Use managed MongoDB with TLS, backups, indexes, and least-privilege credentials.
- Replace in-process background tasks with a durable Redis/Celery, queue, or MongoDB job-claim worker before high-volume deployment.
- Add provider timeouts, exponential backoff with jitter, circuit breakers, quota telemetry, and correlation IDs.
- Batch categorization and embeddings; cache repeated merchant classifications and chat results.
- Pin stable model IDs and validate every structured response.
- Re-embed all Pinecone vectors when changing embedding models or dimensions.
- Add rate limiting, PDF malware/content scanning, secret management, encryption, retention policies, and audit logs.
- Monitor OCR failures, fallback rate, queue age, latency, database/vector errors, and token usage.

Passwords and PDF passwords must never be logged or sent to LLM providers. Mask sensitive transaction fields before AI calls. AI output is advisory; deterministic calculations remain the source of truth for financial totals.

## License

Add the intended project license before public production distribution.
