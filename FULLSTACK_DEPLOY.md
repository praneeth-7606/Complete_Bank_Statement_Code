# Fullstack Deploy — Complete_Bank_Statement_Code

Repo: `praneeth-7606/Complete_Bank_Statement_Code` · Branch: `main`
Local: `C:\Users\prane\Downloads\Complete_Bank_Statement_Code-main\Complete_Bank_Statement_Code-main`
Date: 2026-09-18

## Status

| Part | Platform | Project / Service | Live URL | Status |
|---|---|---|---|---|
| Frontend | Vercel | bank-statement-frontend | https://bank-statement-frontend-blush.vercel.app | LIVE (READY, production) |
| Backend | Render | BANK_STATEMENT_BACKEND (srv-damd95p42hec738l1c0g) | https://bank-statement-backend-wm2i.onrender.com | LIVE (`/` 200, `/docs` 200, `/test-cors` 200, CORS allows Vercel frontend) |

## Frontend (Vercel) — DONE

- Project: `bank-statement-frontend` (team `praneeth-7606s-projects` / `team_uMLmYT7y59eNgRcLM6agskUR`)
- Root dir: `frontend/` · Framework: Vite (auto-detected) · Build: `npm run build` (`vite build`) · Output: `dist`
- Production deployment: `dpl_EwhwZxXq13y64kXkYvcpLnBAvxoV` — status READY, target production
- Production URL: https://bank-statement-frontend-blush.vercel.app
- Aliases: https://bank-statement-frontend-praneeth-7606s-projects.vercel.app
- Env vars (Production):
  - `VITE_API_URL` = `https://bank-statement-backend-wm2i.onrender.com` — live backend (verified baked into production JS bundle)
- Google OAuth has been removed; delete the former `VITE_GOOGLE_CLIENT_ID` variable from the Vercel project before the next deployment.

## Backend (Render) — BLOCKED

- Attempted service creation `BANK_STATEMENT_BACKEND` (runtime python, repo `praneeth-7606/Complete_Bank_Statement_Code`, branch main).
- Intended config: rootDir `backend`, build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, plan free, region oregon.
- Env vars staged from `backend/.env` (names only, values never committed/echoed):
  `GEMINI_API_KEY, HMAC_SECRET_KEY, MONGO_URI, PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME, DEBUG, LOG_LEVEL, SECRET_KEY, ENCRYPTION_KEY, ENCRYPTION_SALT, MISTRAL_API_KEY, GROQ_API_KEY, GROQ_MODEL, GROQ_BASE_URL, ZAI_API_KEY, ZAI_MODEL, ZAI_VISION_MODEL, ZAI_BASE_URL, GROWW_API_KEY, GROWW_API_SECRET, GROWW_MCP_SERVER_COMMAND, GROWW_MCP_SERVER_URL, GEMINI_MODEL, LLM_TIMEOUT_SECONDS, MISTRAL_OCR_MODEL`
- **Result: HTTP 400 — "Hobby Tier is limited to 25 services".** Render workspace `tea-csppiol6l47c73dkc9hg` is at exactly 25 services (MOBILE_APP x2 already deleted).

## Next steps

1. Free a Render slot (delete/archive an unused service) to drop below 25.
2. Create `BANK_STATEMENT_BACKEND` with the config above (rootDir `backend`).
3. Update Vercel `VITE_API_URL` to the live Render URL and redeploy (or it will already match if the placeholder slug is used).
4. Health-check backend `/` and `/health`, then verify frontend → backend calls (CORS already allows localhost dev origins; add the Vercel origin if needed).
