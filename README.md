# Modo Studio Intelligence Desk

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=111111)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-black)

An AI-assisted client experience and operator workspace for Modo Studio. Ren, the public-facing assistant, answers questions from approved studio knowledge, preserves anonymous conversations, and hands visitors to a human operator without losing context.

The project combines a responsive studio website, a retrieval-augmented chatbot, a persistent FastAPI backend, and a protected real-time operator inbox in one repository.

## Product preview

### Embedded client assistant

Ren lives directly inside the Modo Studio website, streams grounded answers, restores previous visitor conversations, and offers an expert handoff when a request needs human attention.

![Modo Studio website with the Ren AI assistant](./homepage-chatbot.png)

### Intelligence Desk

The operator inbox provides conversation search and filtering, visitor presence, complete message history, human takeover, operator replies, return-to-Ren controls, and resolution workflows.

![Modo Studio Intelligence Desk operator inbox](./intelligence-desk.png)

## Highlights

- **Grounded studio answers** — retrieval-augmented responses use only approved Modo Studio knowledge.
- **Live response streaming** — server-sent events deliver status, answer chunks, citations, and completion metadata.
- **Persistent anonymous conversations** — HttpOnly visitor sessions restore multiple threads without exposing credentials to JavaScript.
- **Human handoff** — visitors can record an expert request while operators receive the conversation and its context.
- **Atomic operator takeover** — PostgreSQL row locks prevent Ren and a human operator from owning the same turn concurrently.
- **Protected operator inbox** — admin credentials are exchanged for a signed HttpOnly session rather than stored in browser state.
- **Knowledge operations** — administrators can ingest, replace, inspect, retry, and delete Markdown, text, and text-based PDF documents.
- **Provider isolation** — deterministic providers support repeatable tests; live adapters connect Groq, Pinecone, Hugging Face embeddings, and Jina or a local reranker.
- **Fail-closed production configuration** — missing credentials or unsafe defaults fail validation instead of silently producing mock answers.

## Architecture

```mermaid
flowchart LR
    Visitor[Visitor] --> Web[React + Vite website]
    Operator[Studio operator] --> Desk[Operator inbox]

    Web -->|REST + SSE| API[FastAPI application]
    Desk -->|Protected admin API| API

    API --> Auth[Visitor and admin authorization]
    API --> Chat[Chat orchestration]
    API --> Ops[Handoff and operator workflows]
    API --> Ingest[Knowledge ingestion]

    Auth --> DB[(PostgreSQL / Neon)]
    Chat --> DB
    Ops --> DB
    Ingest --> DB

    Chat --> Groq[Groq LLM]
    Chat --> Embed[Hugging Face embeddings]
    Embed --> Pinecone[(Pinecone index)]
    Pinecone --> Rerank[Jina or local reranker]
    Rerank --> Chat

    Ingest --> Embed
    Ingest --> Pinecone
```

### Chat request lifecycle

1. The browser creates or restores an anonymous visitor session and conversation.
2. FastAPI authenticates the conversation and locks its row to serialize concurrent turns.
3. The router classifies the request as knowledge, clarification, handoff, or action.
4. Knowledge questions are embedded and queried against the configured Pinecone collection.
5. Weak candidates are removed and the remaining evidence is reranked.
6. Groq generates an answer constrained to the retrieved evidence and Modo Studio's versioned assistant rules.
7. The finalized answer is streamed to the browser and persisted with structured source metadata.
8. Reusing the same request ID returns the stored result, preventing duplicate turns after retries.

Provider clients and local models are initialized lazily. Importing the application does not contact external services or download an embedding model.

## Technology stack

| Layer | Technology | Responsibility |
|---|---|---|
| Web application | React 19, TypeScript, Vite 8 | Public website, chat experience, and operator dashboard |
| UI system | Tailwind CSS 4, Radix UI, Lucide | Responsive layout, accessible primitives, and icons |
| API | FastAPI, Uvicorn, Pydantic | Typed REST endpoints, SSE streaming, validation, and OpenAPI |
| Persistence | PostgreSQL, SQLAlchemy 2, asyncpg | Conversations, messages, sessions, handoffs, knowledge metadata, and idempotency |
| Schema management | Alembic | Versioned PostgreSQL migrations |
| Language model | Groq | Routing, standalone retrieval queries, summaries, and grounded responses |
| Embeddings | Sentence Transformers / BGE | Normalized semantic vectors |
| Vector search | Pinecone | Namespaced knowledge retrieval |
| Reranking | Jina AI or local CrossEncoder | Final evidence ordering |
| Testing | Pytest, Vitest, Testing Library | Backend integration and frontend component coverage |
| Quality | Ruff, Oxlint, TypeScript | Python linting, frontend linting, and static type checking |
| Automation | GitHub Actions | PostgreSQL-backed backend checks and frontend CI |

## Repository structure

```text
modo-studio-intelligence-desk/
├── app/                     FastAPI application
│   ├── api/                 Routes and request dependencies
│   ├── core/                Settings, security, and shared errors
│   ├── db/                  SQLAlchemy engine and models
│   ├── providers/           Deterministic and live AI providers
│   ├── schemas/             Public API contracts
│   └── services/            Chat, retrieval, ingestion, memory, and handoffs
├── config/                  Versioned business and assistant behavior
├── frontend/                React website, Ren chat, and operator inbox
├── knowledge/source/        Approved Markdown knowledge documents
├── migrations/              Alembic migrations
├── scripts/                 Knowledge and operational utilities
├── tests/                   Backend integration tests and fixtures
├── design/                  Original supplied design assets
├── docs/                    Architecture, handoff, plans, and references
├── compose.yaml             Local API and PostgreSQL services
├── compose.test.yaml        Disposable PostgreSQL test service
└── Dockerfile               Backend container image
```

See [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md) for detailed ownership boundaries.

## Getting started

### Prerequisites

- Python 3.11 or newer; CI uses Python 3.12
- Node.js 22 and npm
- PostgreSQL 16 locally, or a managed PostgreSQL service such as Neon
- Docker only if you want the included local/test PostgreSQL services

### 1. Clone and configure

```powershell
git clone https://github.com/hammadproject/modo-studio-intelligence-desk.git
Set-Location modo-studio-intelligence-desk
Copy-Item .env.example .env
```

Fill `.env` with your own development values. Never commit `.env`; the repository tracks only `.env.example`.

### 2. Install the backend

For deterministic development and backend tests:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

For live Groq, Pinecone, and embedding providers:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-live.txt
```

### 3. Prepare PostgreSQL

Start the included local database:

```powershell
docker compose up -d db
.\.venv\Scripts\python.exe -m alembic upgrade head
```

If `DATABASE_URL` points to Neon or another managed PostgreSQL instance, Docker is unnecessary. Apply migrations only to a database you explicitly intend to modify.

### 4. Install the frontend

```powershell
npm.cmd --prefix frontend ci
```

### 5. Run both applications

Backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend, in a second terminal:

```powershell
npm.cmd --prefix frontend run dev -- --host 127.0.0.1
```

Open:

- Website: <http://127.0.0.1:5173>
- Operator inbox: <http://127.0.0.1:5173/admin>
- API documentation: <http://127.0.0.1:8000/docs>
- Readiness: <http://127.0.0.1:8000/health/ready>

The frontend derives its default API hostname from the page hostname. Set `VITE_API_BASE_URL` only when the API is hosted elsewhere; never place server credentials in a `VITE_` variable.

## Provider modes

### Deterministic mode

`PROVIDER_MODE=deterministic` provides network-free, repeatable behavior for development and automated tests. It is explicit—production validation will not permit deterministic mode.

### Live mode

Live mode requires:

- `PROVIDER_MODE=live`
- A Groq API key
- A Pinecone API key
- An existing Pinecone index matching `EMBEDDING_DIMENSION`
- A Jina API key when `RERANKER_PROVIDER=jina`
- Non-default admin and conversation-token secrets

The application does not create or reset external Pinecone indexes automatically.

## Configuration

All supported settings are documented in [`.env.example`](.env.example). The primary groups are:

| Group | Key settings |
|---|---|
| Runtime | `ENVIRONMENT`, `PROVIDER_MODE`, `LOG_LEVEL`, `CORS_ALLOW_ORIGINS` |
| Database | `DATABASE_URL` |
| Security | `ADMIN_API_KEY`, `CONVERSATION_TOKEN_PEPPER`, session and cookie settings |
| LLM | `LLM_PROVIDER`, `LLM_MODEL`, `GROQ_API_KEY` |
| Embeddings | `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION` |
| Retrieval | `PINECONE_API_KEY`, `VECTOR_INDEX_NAME`, `VECTOR_COLLECTION`, candidate and top-k limits |
| Reranking | `RERANKER_PROVIDER`, local/Jina model settings, `JINA_API_KEY` |
| Memory | History budget and summary trigger settings |
| Limits | Message, upload, chunking, timeout, retry, and rate-limit settings |

For Neon deployments, use the pooled application connection string when appropriate and retain Neon's required SSL parameters. Keep direct administrative URLs separate from public configuration.

## Knowledge ingestion

Approved source material lives in [`knowledge/source/`](knowledge/source/). With the API running and authorized configuration available, ingest the packaged Modo Studio documents with:

```powershell
.\.venv\Scripts\python.exe -m scripts.ingest_modo
```

Ingestion behavior includes:

- `.txt`, `.md`, and text-based `.pdf` input
- Heading-aware Markdown chunking
- Deterministic document, chunk, and vector identities
- No-op handling for unchanged documents
- Replacement of stale vectors when content changes
- Partial-failure state with safe retry support
- Collection-scoped retrieval and structured citation metadata

OCR, website scraping, and automatic external-index creation are intentionally outside the current scope.

## API overview

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| `GET` | `/health/live` | Public | Process liveness |
| `GET` | `/health/ready` | Public | Database, provider, and knowledge readiness |
| `POST` | `/api/v1/conversations` | Public | Create a visitor conversation |
| `GET` | `/api/v1/visitor/conversations` | Visitor session | Restore the visitor's conversations |
| `POST` | `/api/v1/conversations/{id}/messages` | Conversation | Submit an idempotent chat turn |
| `POST` | `/api/v1/conversations/{id}/messages/stream` | Conversation | Stream status, answer chunks, and completion |
| `GET` | `/api/v1/conversations/{id}/messages` | Conversation | Read ordered history |
| `POST` | `/api/v1/conversations/{id}/handoffs` | Conversation | Record an expert request |
| `POST` | `/api/v1/admin/session` | Admin key | Create an HttpOnly admin session |
| `GET` | `/api/v1/admin/conversations` | Admin session | Search and filter the operator inbox |
| `POST` | `/api/v1/admin/conversations/{id}/takeover` | Admin session | Transfer the thread to an operator |
| `POST` | `/api/v1/admin/conversations/{id}/messages` | Admin session | Send an operator reply |
| `POST` | `/api/v1/admin/conversations/{id}/release` | Admin session | Return the thread to Ren |
| `POST` | `/api/v1/admin/conversations/{id}/resolve` | Admin session | Resolve the thread |
| `POST` | `/api/v1/admin/knowledge/documents` | Admin credential | Ingest or replace knowledge |
| `POST` | `/api/v1/admin/knowledge/documents/{id}/retry` | Admin credential | Retry partial indexing |
| `DELETE` | `/api/v1/admin/knowledge/documents/{id}` | Admin credential | Remove a document and its vectors |

The complete interactive contract is available through FastAPI at `/docs`.

## Security model

- Conversation identifiers are not credentials.
- Browser visitors use an opaque HttpOnly session; bearer conversation credentials remain available for non-browser clients.
- Only keyed hashes of conversation and visitor credentials are stored.
- Admin keys are exchanged for signed, time-limited HttpOnly sessions.
- Every history and message operation is scoped to its authorized conversation.
- PostgreSQL row locks serialize concurrent turns and operator state transitions.
- Request IDs enforce idempotency and make failed turns safely retryable.
- Retrieved source metadata is generated only from approved indexed chunks.
- Provider credentials, database credentials, admin keys, and token peppers remain server-side.
- Logs omit conversation bodies by default and include correlation IDs for operations.
- Document and message sizes, CORS origins, provider timeouts, retries, and per-IP request rates are bounded.

The built-in rate limiter is process-local. Production deployments with multiple API instances should enforce distributed limits at an edge gateway or shared store.

## Verification and tests

### Backend

The backend suite requires a disposable PostgreSQL database. Never point these tests at production because the fixtures truncate test tables.

```powershell
docker compose -f compose.test.yaml up -d --wait
$env:DATABASE_URL='postgresql+asyncpg://chirpy_test:chirpy_test@localhost:55432/chirpy_test'
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m ruff check app migrations scripts tests
.\.venv\Scripts\python.exe -m pytest -q
docker compose -f compose.test.yaml down
```

### Frontend

```powershell
npm.cmd --prefix frontend run typecheck
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run test -- --run
npm.cmd --prefix frontend run build
```

GitHub Actions runs the same backend checks against an isolated PostgreSQL 16 service and performs the complete frontend verification pipeline.

## Operational behavior

- `/health/live` confirms that the process is accepting requests.
- `/health/ready` distinguishes database, provider configuration, and knowledge-base availability.
- An empty knowledge base reports degraded readiness rather than pretending grounded answers are available.
- Provider failures return typed service errors and leave idempotent requests retryable.
- Human handoffs report only what has actually been recorded; the system does not promise response times.
- Conversation deletion cascades through dependent messages, requests, handoffs, and tool executions.
- External vectors are removed before knowledge metadata is deleted.
- There is deliberately no bulk database or vector-index reset endpoint.

## Documentation

- [Project structure](docs/PROJECT_STRUCTURE.md)
- [GitHub, Neon, and deployment handoff](docs/GITHUB_NEON_HANDOFF.md)
- [Frontend notes](frontend/README.md)
- [Implementation plans](docs/plans/)

## Roadmap

- Replace polling with distributed real-time operator events
- Add multi-operator accounts, roles, and audit history
- Add external email, Slack, or push handoff notifications
- Optimize operator-inbox aggregation for high-latency managed databases
- Add production observability and distributed rate limiting
- Expand knowledge-source connectors with explicit review and approval workflows

## License

Released under the [MIT License](LICENSE).
