# Modo Studio Intelligence Desk — Implementation Plan

## Instructions to Codex

Read this entire plan and inspect the workspace and any AGENTS.md instructions first. Then implement Phase 1, validate it, and report results. Do not stop at describing a plan. Do not implement Phases 2 or 3, select a niche, invent business policies, build a dashboard, or deploy anything. Make routine engineering decisions autonomously and document them. If external credentials are unavailable, finish everything that can run locally with deterministic test adapters and identify the remaining live integration checks honestly.

## Project context and goal

Modo Studio Intelligence Desk is the AI-assisted client experience for Modo Studio. It combines a customer-facing assistant, grounded agency knowledge, conversation history, handoffs, and an operator inbox.

The future possibility of customers creating and embedding their own bots is outside the current scope. Build one configurable assistant, not a multi-tenant SaaS bot builder.

Work proceeds in three phases:
1. Domain-neutral backend architecture, pipelines, configuration, conversation memory, and persistent data.
2. Choose the business niche, prepare its knowledge base, ingest documents, and configure its specific behavior and actions.
3. Build the Modo Studio website and Intelligence Desk chat widget. A custom dashboard is separate future work.

## Starting repository

https://github.com/Pratham1603/sezzle-ai-customer-support-agent

Use this repository as a starting point, not as an unquestioned specification. If no project exists, clone it into an appropriate project directory. If the workspace already contains our project, inspect it and adapt without overwriting unrelated work or adding a nested clone. Record the upstream revision used. Preserve the upstream MIT license and copyright notices, and document attribution in the README.

The upstream architecture includes FastAPI, LangChain, Groq, HuggingFace embeddings, Pinecone, SQLite logs, React, and Streamlit. Its limitations include hardcoded mock orders, stateless API requests, a cosmetic voice screen, retrieval similarity presented as confidence, and a fallback message presented as human escalation.

Remove Sezzle branding, data, policy prompts, phone numbers, order/refund/cancellation code, business-specific intent labels, old deployment URLs, and the Streamlit dashboard/dependencies. Remove the old React demo from the active project or clearly archive it outside the runnable application; no frontend implementation in Phase 1. Keep API documentation through FastAPI OpenAPI. Do not retain old mock business actions as Intelligence Desk features.

## Phase 1 defaults

Use Python 3.11+, FastAPI, Pydantic settings, SQLAlchemy, Alembic, and PostgreSQL. Provide local PostgreSQL through Docker Compose with a persistent volume; allow a Neon PostgreSQL connection through DATABASE_URL without requiring Neon to finish local work. Use PostgreSQL in integration tests rather than assuming SQLite has equivalent behavior.

Retain Groq for the initial LLM adapter, BAAI/bge-base-en-v1.5 for local embeddings, and Pinecone for the initial vector adapter unless inspection exposes a concrete compatibility problem. Make provider names, model names, index name, dimensions, thresholds, top-k, and timeouts configurable. Do not hardcode a model into application logic. Resolve compatible package versions and provide reproducible dependency installation. Do not assume the upstream pins are valid.

Keep provider interfaces small. One real adapter per capability plus deterministic test adapters is sufficient. Do not add unnecessary orchestration frameworks, Redis, background workers, or multiple providers. LangChain may be retained where helpful; conversation memory must be owned by our database and service code.

## Suggested organization

Use a maintainable layout such as app/api, app/core, app/db, app/models, app/schemas, app/services, app/providers, app/prompts, migrations, scripts, and tests. Separate HTTP routes from conversation orchestration, ingestion, retrieval, persistence, and provider clients. Use dependency injection so tests do not need network calls or API keys.

## Required configuration and startup behavior

- Provide .env.example with placeholders and descriptions, never real secrets.
- Configure database, LLM, embeddings, vector store, business configuration path, CORS allowlist, API limits, and logging.
- Load business identity and neutral assistant instructions from a versioned configuration file. Do not choose a niche or fabricate services, pricing, timelines, or contact details.
- Do not download embedding models or call hosted providers on module import. Initialize clients lazily or through managed application lifecycle.
- Provide liveness and readiness endpoints. Readiness must distinguish database readiness, provider configuration, and an empty knowledge base; an empty knowledge base is an expected Phase 1 state.
- Use explicit production configuration validation. Missing secrets must never silently enable fake answers. Test/demo adapters require an explicit mode and responses must identify that mode.

## Conversation persistence and memory

Create migrations for:
- Conversations: UUID, access-token hash, status, structured state JSON, optional summary and summary boundary, UTC creation/update timestamps.
- Messages: UUID, conversation ID, ordered sequence, role, content, UTC timestamp, request ID, and useful response/tool metadata.
- Chat requests: idempotency key, conversation ID, input hash, processing status, and saved response; equivalent schema is acceptable.
- Knowledge documents/chunks: content hash, version, source metadata, indexing status, and vector identifiers.
- Handoff requests: conversation ID, reason, status, UTC timestamp, and optional consented contact details.

Persist user and assistant messages, tool results when present, and pending interaction state. Database logs are separate from conversational memory. Every query must be scoped to the authorized conversation.

Create a conversation through the backend and return an opaque access token once. Require the token for chat and history endpoints; a UUID alone is not authorization. Store only its hash. This is anonymous conversation access, not customer-account authentication. Administrative operations require a separately configured admin credential.

Load a configurable recent history window within a token budget. Maintain a rolling summary for older turns only when needed; summarize only confirmed conversational information, retain original messages, and record which messages were summarized. Structured state is authoritative for pending actions. A summary must not replace business policies or verified tool results.

Handle repeated requests idempotently: the same request ID and payload returns the saved result; reuse with different input is rejected. Serialize concurrent turns per conversation or reject overlapping requests with a documented retryable response. A failed turn must be marked clearly and remain retryable without duplicate successful messages or side effects.

## Domain-neutral chat and RAG flow

1. Authenticate conversation access and validate message limits/request ID.
2. Load recent history, summary, and structured state.
3. Persist the incoming turn and classify its route using current message plus relevant memory.
4. Route to knowledge answering, clarification, handoff, or a registered action. Use validated structured output and a neutral intent schema. Do not execute arbitrary generated code.
5. For ambiguous follow-ups, produce a standalone retrieval query using conversation context. Avoid an extra rewrite call for already self-contained questions where possible.
6. Retrieve documents once; reuse those same results for the relevance gate and answer context. Preserve source identifiers and metadata.
7. If the knowledge base is empty or evidence is insufficient, return a clear fallback or clarification, never fabricated business information. Offer the configured handoff route when applicable.
8. Generate an answer using separate system instructions, history, and retrieved evidence. Return structured source citations linked to retrieved documents, not invented URLs.
9. Save the answer, route, retrieval metadata, tool results, and updated state before returning.

Treat retrieval scores as relevance signals, not calibrated answer confidence or percentages. Document the vector adapter's score semantics and configurable thresholds. Scope retrieval to the configured knowledge collection and support metadata filters. Do not add hybrid search or reranking until evaluation justifies it.

## Ingestion pipeline

Provide an admin-only CLI or API that supports UTF-8 text, Markdown, and text-based PDFs. OCR and website scraping are outside Phase 1. Reject unsupported files and flag PDFs with no extractable text.

Preserve document title, source, version/hash, chunk identifiers, and optional source URL. Make chunk size and overlap configurable and validate embedding dimensions against the vector index. Support repeatable ingestion without duplicate vectors through deterministic IDs/content hashes. Track partial failures so retries complete missing work instead of treating a partially populated index as complete. Define replace/delete behavior so stale chunks do not remain searchable. Destructive index resets must require an explicit operator flag.

Include clearly labeled synthetic test documents under tests/fixtures only. Do not seed them into the default business knowledge collection. An API smoke test may ingest them into an isolated test namespace.

## Tools and human handoff

Implement a tool registry with typed input/output schemas and a small service boundary. No domain-specific booking or order tools yet. Validate inputs and store execution results. Support a pending-confirmation state so Phase 2 can safely add actions with side effects. Do not simulate successful actions when no integration exists.

Implement a real persistent handoff-request action and API endpoint. It creates a request associated with the conversation and returns its actual status. Until a staff interface/notification integration exists, describe it as a recorded handoff request; do not claim a person has joined, been notified, or will respond within an invented time. Live chat takeover and scheduling an expert call are later integrations.

## API contract

Use a consistent versioned JSON API, for example:
- POST /api/v1/conversations: create conversation and return access token.
- POST /api/v1/conversations/{id}/messages: submit message and request ID.
- GET /api/v1/conversations/{id}/messages: authorized paginated history.
- POST /api/v1/conversations/{id}/handoffs: record handoff request.
- Admin CLI/API: ingest, list indexing status, replace, and delete knowledge documents.
- GET /health/live and GET /health/ready.

Chat responses should consistently include conversation ID, request ID, assistant message ID, answer, route, sources, handoff status where relevant, and provider mode. Define typed error responses. Do not expose raw prompts, stack traces, credentials, or another session's information. Streaming is optional future work; ordinary JSON is sufficient now.

## Reliability and operational basics

Use asynchronous provider clients or move blocking embedding/vector calls off the event loop. Add bounded timeouts and retries for transient provider failures; never blindly retry side effects. Separate application errors from provider outages and empty retrieval. Add request correlation IDs and latency logging without logging secrets or full customer conversations by default.

Use a configured CORS allowlist, input/upload size limits, and basic abuse limits with documented single-instance scope. Protect knowledge-management endpoints. Provide a conversation deletion operation or CLI that removes associated messages/state and document its retention behavior. No full account system or enterprise security stack is required in Phase 1.

Provide Dockerfile, Compose configuration, database migrations, README, .env.example, reproducible dependencies, and sample API commands. Do not deploy or configure external accounts automatically.

## Validation and Phase 1 acceptance criteria

Run meaningful automated tests with deterministic LLM/vector adapters and a real local PostgreSQL test database. Cover:
- Session isolation and access-token enforcement.
- History/state persistence after recreating application instances.
- Follow-up resolution using previous turns, with no cross-conversation leakage.
- Rolling summary boundary and bounded history behavior.
- Empty knowledge base and low-relevance fallbacks.
- Single retrieval per answer and sources restricted to retrieved documents.
- Repeated ingestion, changed documents, partial indexing failure/retry, and stale-vector removal.
- Idempotent requests and conflicting/concurrent turns.
- Provider failure without fabricated success.
- Handoff persistence with truthful status.
- Administrative endpoint protection.

Acceptance requires a clean migration to PostgreSQL, successful local API smoke test, passing relevant tests, and no active Sezzle/Streamlit business code. Retained license/attribution may mention the upstream project. Verify real adapters with available credentials if present; otherwise report these as unverified and provide exact commands for the user to run. Do not claim mocked tests prove live provider integration.

## Implementation milestones

1. Inspect upstream/workspace; preserve attribution; remove business-specific components.
2. Establish project structure, settings, dependency installation, Docker, and migrations.
3. Build persistence, conversation authorization, request ordering, and memory.
4. Build provider adapters, ingestion, retrieval, evidence gate, and chat orchestration.
5. Add typed tool interfaces and persistent handoff requests.
6. Test, document, and deliver Phase 1.

At completion, report what changed, test results, setup/run commands, required environment variables, any unresolved integration checks, and the Phase 2 handoff. Stop before selecting the business domain or building the frontend.

## Phase 2 — deferred

Choose the fictional business and niche with the user. Define its identity, services, policies, tone, contact options, knowledge sources, and permitted actions. Prepare and ingest approved documents. Tune retrieval using representative questions and follow-ups. Implement business integrations and confirmations as needed. Never infer unprovided policies or imply a fictional business is a real client.

## Phase 3 — deferred

Build the Modo Studio website and responsive Intelligence Desk chat widget. Add new-chat controls, history restoration, sources, and a Talk to an expert entry point connected to the backend's actual handoff workflow. Store conversation credentials appropriately for the eventual frontend. Use Modo Studio branding throughout. Test end-to-end. Build no Streamlit dashboard; a custom dashboard is future work.
