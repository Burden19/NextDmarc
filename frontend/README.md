# NextDmarc Frontend

Next.js (React) frontend for the NextDmarc DMARC analysis platform. The UI is aligned with the four-actor governance model and mirrors the conception artifacts in `complete_conception/four_actors`.

## Stack
- Next.js (Pages Router)
- JavaScript
- Material UI + Tailwind CSS

## Quick start
```bash
npm install
npm run dev
```

## Environment
- `NEXT_PUBLIC_API_BASE_URL` (optional): backend API base URL.
- Default value in code: `http://localhost:8000/api/v1`.

Example `.env.local`:
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

## Available scripts
- `npm run dev` - start local dev server
- `npm run build` - production build
- `npm run start` - run the production build
- `npm run lint` - eslint checks

## Structure
- `src/pages` - route pages (dashboard, domains, reports, alerts, scoring, governance, integrations)
- `src/components` - layout and reusable UI cards
- `src/lib/apiClient.js` - shared API request helper with auth headers and refresh retry
- `src/lib/authSession.js` - auth session persistence and login/register helpers
- `src/theme.js` - MUI theme with blue brand palette

## Notes
- The sidebar and top bar reflect the SOC-friendly navigation.
- Login and data pages are wired to backend APIs and tenant-scoped headers.

