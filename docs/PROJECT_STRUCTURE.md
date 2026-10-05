# Project structure

This repository contains two deployable applications and their supporting material:

- the FastAPI chatbot backend at the repository root;
- the React website and chat client in `frontend/`.

Knowledge documents, design source files, and planning references are deliberately kept outside the runtime applications.

```text
modo-studio-intelligence-desk/
|-- app/                         FastAPI chatbot backend
|   |-- api/                     HTTP routes and request dependencies
|   |-- core/                    Settings, security, and shared errors
|   |-- db/                      SQLAlchemy database models and connection setup
|   |-- providers/               Groq, embeddings, Pinecone, and rerankers
|   |-- schemas/                 API request and response models
|   `-- services/                Chat, retrieval, ingestion, memory, and handoffs
|-- config/                      Versioned business and assistant behavior
|-- migrations/                  Alembic PostgreSQL migrations
|-- scripts/                     Operational scripts such as knowledge ingestion
|-- tests/                       Backend tests and fixtures
|-- frontend/                    React/Vite Modo Studio website and chat client
|   |-- public/                  Images shipped directly with the website
|   `-- src/
|       |-- components/          Website sections, chat UI, and reusable UI pieces
|       |-- data/                Static website content
|       |-- hooks/               Stateful client behavior and API streaming
|       |-- test/                Frontend test setup
|       `-- types/               Shared TypeScript API types
|-- knowledge/
|   `-- source/                  Approved Markdown documents ingested into Pinecone
|-- design/
|   `-- source-assets/           Original supplied imagery before web optimization
|-- docs/
|   |-- plans/                   Historical implementation plans
|   `-- design-references/       UI references and generated design concepts
|-- Dockerfile                   Backend container image
|-- compose.yaml                 Local backend and PostgreSQL services
|-- compose.test.yaml            Isolated PostgreSQL service for backend tests
|-- alembic.ini                  Migration configuration
|-- requirements*.txt            Backend dependency groups
|-- .env.example                 Backend environment-variable template
`-- README.md                    Main setup and architecture guide
```

## Backend ownership

The complete chatbot backend consists of:

- `app/` for application code;
- `config/` for Ren and Modo Studio behavior configuration;
- `migrations/` and `alembic.ini` for PostgreSQL schema changes;
- `scripts/` for administrative operations;
- `tests/` for backend verification;
- `requirements*.txt`, `Dockerfile`, and Compose files for installation and runtime infrastructure.

Within `app/`:

- `api/` exposes conversations, messages, streaming, handoffs, health checks, and knowledge administration endpoints.
- `core/` loads environment settings and contains authorization/security helpers.
- `db/` defines persistent conversations, messages, knowledge metadata, handoffs, and request records.
- `providers/` isolates external services. Live mode uses Groq, Pinecone, embeddings, and a local or Jina reranker; deterministic mode supports repeatable tests.
- `services/` contains the actual workflows: routing a message, retrieving evidence, generating and formatting an answer, managing memory, ingesting documents, and recording handoffs.
- `schemas/` defines the public API contract.

## Frontend ownership

`frontend/` is the complete browser application. It contains the public Modo Studio website, responsive styling, expert-request form, and Ren chat widget. It communicates with FastAPI but never receives the admin key, provider keys, database credentials, or conversation-token pepper.

Runtime images belong in `frontend/public/`. The similarly named files under `design/source-assets/` are editable/original source material and are not served automatically.

## Knowledge and configuration

These folders serve different purposes:

- `knowledge/source/` contains business facts written for ingestion and retrieval.
- `config/business.v1.json` contains compact business-answering instructions.
- `config/assistant.v1.json` contains Ren's persona, general intents, safe language, fallbacks, and response behavior.

After editing the Markdown knowledge, run this from the repository root:

```powershell
.\.venv\Scripts\python.exe -m scripts.ingest_modo
```

## Design and planning material

- `design/source-assets/` preserves original supplied images.
- `docs/design-references/` contains visual references and dashboard concepts; these files are not loaded by the website.
- `docs/plans/` records earlier implementation plans for project history. They are documentation, not runtime configuration.

## Admin dashboard

The operator dashboard lives at `/admin` and its components are under `frontend/src/components/admin/`. It exchanges the admin key for an HttpOnly session cookie, polls the protected inbox for near-real-time updates, and supports takeover, operator replies, return-to-Ren, and resolution. Its secure endpoints and conversation state machine live in the existing FastAPI backend. The original dashboard concept is stored at `docs/design-references/modo-admin-dashboard-concept.png`.
