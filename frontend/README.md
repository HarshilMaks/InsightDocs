# InsightDocs frontend

The frontend is a React and TypeScript application built with Vite. It provides the authenticated document library, evidence chat, Evidence Workspaces, History, and review views.

## Local development

```bash
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

The development server listens on `http://localhost:3000`.

Set `VITE_API_BASE_URL` in `.env.local` to the complete FastAPI API base URL, including `/api/v1`. The frontend does not use or expose a Gemini API key.

## Checks

```bash
npm run lint
npm run build
```

## Deployment

Build output is written to `dist/`. Configure `VITE_API_BASE_URL` in the hosting environment before the build. See [the root deployment guide](../DEPLOYMENT.md) for the API, worker, CORS, and release sequence.
