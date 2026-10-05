# GitHub, Neon, and new-computer handoff

This repository is prepared for a private GitHub workflow. The new computer does not need Docker to run the application: it can connect directly to a Neon PostgreSQL database.

## What is and is not stored in Git

Commit the application, migrations, approved Markdown, images, lockfiles, and `.env.example` files. Never commit `.env`, database dumps, virtual environments, `node_modules`, build output, logs, or provider caches. Transfer the real `.env` through an encrypted channel and configure the same secrets in the deployment providers' dashboards.

Before the first push, confirm that this command prints no tracked secret file:

```powershell
git ls-files | Select-String -Pattern '(^|/)(\.env|\.venv|node_modules|dist)(/|$)'
```

## Prepare Neon without reingesting Pinecone

Pinecone already contains the vectors, but the API also requires the matching PostgreSQL rows in `knowledge_documents` and `knowledge_chunks`. Create the Neon database and run the schema migrations first:

```powershell
$env:DATABASE_URL='<NEON_CONNECTION_STRING>'
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Then copy only `knowledge_documents` and `knowledge_chunks` from the current local PostgreSQL database into Neon. Do this once on the current computer, where Docker and the populated database are available:

```powershell
# SOURCE_DATABASE_URL is optional; when omitted, the script uses DATABASE_URL from .env.
$env:TARGET_DATABASE_URL='<NEON_CONNECTION_STRING>'
.\.venv\Scripts\python.exe -m scripts.copy_knowledge_metadata
Remove-Item Env:TARGET_DATABASE_URL
```

The command refuses to write over existing target knowledge unless `--replace` is explicitly supplied. It does not copy visitor sessions, conversations, messages, chat requests, handoffs, or tool executions. Preserving the knowledge UUIDs and vector IDs keeps the existing Pinecone data usable without another ingestion run.

Use the pooled Neon connection string for the running API. The application accepts Neon's standard `postgresql://...?...sslmode=require&channel_binding=require` URL and adapts it for both asyncpg and Alembic automatically.

## Push from the current computer

Create an empty private repository on GitHub, then run:

```powershell
git add .
git status
git commit -m "Prepare Modo Studio Intelligence Desk"
git branch -M main
git remote add origin <PRIVATE_GITHUB_REPOSITORY_URL>
git push -u origin main
```

Review `git status` before committing. The real `.env` must not appear in the staged files.

## Clone and run without Docker

Install Git, Python 3.12, and Node.js 22 on the new computer. Then run:

```powershell
git clone <PRIVATE_GITHUB_REPOSITORY_URL>
cd modo-studio-intelligence-desk

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-live.txt
npm --prefix frontend ci
```

Copy the real `.env` into the repository through an encrypted channel. Its `DATABASE_URL` must be the Neon URL, not the old localhost URL. Start the applications:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
npm --prefix frontend run dev
```

No local PostgreSQL or Docker service is required. The local backend connects to Neon, Groq, Pinecone, and Jina over HTTPS/TLS.

## Deploy the frontend to Vercel

Import the private GitHub repository into Vercel and use:

- Root Directory: `frontend`
- Framework Preset: Vite
- Install Command: `npm ci`
- Build Command: `npm run build`
- Output Directory: `dist`
- Environment variable: `VITE_API_BASE_URL=https://<BACKEND_DOMAIN>`

`frontend/vercel.json` provides the SPA fallback required when `/admin` is opened or refreshed directly.

Only `VITE_API_BASE_URL` belongs in the frontend project. Database and provider secrets must be configured on the backend host.

## Production environment changes

The transferred local `.env` is a useful source, but production requires these value changes:

- `ENVIRONMENT=production`
- `PROVIDER_MODE=live`
- `DATABASE_URL=<NEON_POOLED_CONNECTION_STRING>`
- `RERANKER_PROVIDER=jina`
- `CORS_ALLOW_ORIGINS=<EXACT_VERCEL_AND_CUSTOM_FRONTEND_ORIGINS>`
- `VISITOR_COOKIE_SAMESITE=none` only while the frontend and API are on genuinely different sites; keep `lax` when both use subdomains of the same parent domain

Keep `GROQ_API_KEY`, `PINECONE_API_KEY`, `JINA_API_KEY`, `VECTOR_INDEX_NAME`, `VECTOR_COLLECTION`, `ADMIN_API_KEY`, and `CONVERSATION_TOKEN_PEPPER` private.
