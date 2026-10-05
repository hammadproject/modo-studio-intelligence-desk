# Modo Studio frontend

Responsive React website and Ren chat client for Modo Studio. It uses Vite, TypeScript, Tailwind CSS v4, and small shadcn-style primitives built on Radix UI.

## Run locally

Start the FastAPI service on port 8000, then run:

```powershell
Copy-Item .env.example .env
npm install
npm run dev
```

Open `http://localhost:5173`. `VITE_API_BASE_URL` defaults to `http://localhost:8000`; set it in `frontend/.env` when the API is elsewhere. All `VITE_` variables are exposed to the browser, so never put the admin API key, Groq/Pinecone keys, database credentials, or conversation-token pepper in this file.

The backend development CORS configuration permits `http://localhost:5173` and `http://127.0.0.1:5173`. Use an explicit deployed origin in production rather than a wildcard.

## Commands

```powershell
npm run typecheck
npm run lint
npm test
npm run build
```

## Implementation notes

- Approved hero, portfolio, logo, and contact imagery is served from `public/`; reusable content metadata lives in `src/data/content.ts`.
- Anonymous conversation credentials and the in-tab conversation index live only in `sessionStorage`. A tab refresh can restore multiple threads without exposing the admin key; closing the tab clears this browser-held history.
- Chat responses use the authenticated server-sent-events endpoint. Ren shows a thinking indicator before the first response chunk and renders finalized Markdown progressively. Retrieval sources remain backend metadata and are not displayed to visitors.
- Failed message retries reuse the original request ID to preserve backend idempotency.
- The expert form places a handoff request in the protected operator inbox. It does not promise a response time.
- The operator dashboard is available at `/admin`; the entered admin key is exchanged for an HttpOnly session cookie and is never stored in frontend state or browser storage.
- Manrope and Archivo Black are bundled from Fontsource. Both are openly licensed under the SIL Open Font License.
