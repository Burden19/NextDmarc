# NextDmarc Frontend

Next.js frontend for the NextDmarc DMARC platform.
The UI is fully wired to backend APIs and no longer depends on `src/data/mock.js`.

## Stack

- Next.js 14 (Pages Router)
- React 18 (JavaScript)
- Material UI + Tailwind CSS

## Quick Start

From `frontend/`:

```bash
npm install
npm run dev
```

App URL: `http://localhost:3000`

## Environment

- `NEXT_PUBLIC_API_BASE_URL` (optional): backend API base URL.
- Default value: `http://localhost:8000/api/v1`.

Example `.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

## Available Scripts

- `npm run dev` - start local dev server
- `npm run build` - production build
- `npm run start` - run production build
- `npm run lint` - eslint checks

## Current Frontend Integration Scope

Auth/session foundation:
- `src/lib/authSession.js` handles register/login/refresh/logout and session persistence.
- `src/lib/apiClient.js` injects auth headers, forwards CSRF header on writes, and retries once after refresh on 401.

Pages wired to backend data:
- `src/pages/index.js`
- `src/pages/dashboard.js`
- `src/pages/domains.js`
- `src/pages/reports.js`
- `src/pages/alerts.js`
- `src/pages/recommendations.js`
- `src/pages/integrations.js`
- `src/pages/scoring.js`

Implemented workflows:
- Alerts triage actions and realtime updates via WebSocket.
- Recommendations resolve and reopen actions.
- Integrations create, test, enable/disable, and delete actions.

## Role Model

Roles are defined in `src/access/roles.js`:

- `nextstep_admin`
- `client_admin`
- `analyst_soc`
- `client_user`

## Validation

Run from `frontend/`:

```bash
npm run lint
npm run build
```

## Notes

- Frontend requests are tenant-scoped and role-aware.
- For browser WebSocket compatibility, backend supports tenant id in query parameter fallback.

