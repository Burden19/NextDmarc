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

## Available scripts
- `npm run dev` - start local dev server
- `npm run build` - production build
- `npm run start` - run the production build
- `npm run lint` - eslint checks

## Structure
- `src/pages` - route pages (dashboard, domains, reports, alerts, scoring, governance, integrations)
- `src/components` - layout and reusable UI cards
- `src/data/mock.js` - placeholder data (replace with API wiring)
- `src/theme.js` - MUI theme with blue brand palette

## Notes
- The sidebar and top bar reflect the SOC-friendly navigation.
- Replace `mock.js` with real API calls as the backend is implemented.

