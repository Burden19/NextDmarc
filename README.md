# NextDmarc

<p align="center">
  <strong>Role-based DMARC monitoring platform with a modern SOC-oriented interface.</strong>
</p>

<p align="center">
  <img alt="Frontend" src="https://img.shields.io/badge/Frontend-Next.js%2014-111827?logo=next.js" />
  <img alt="UI" src="https://img.shields.io/badge/UI-Material%20UI%20%2B%20Tailwind-0f4c97" />
  <img alt="Status" src="https://img.shields.io/badge/Status-Active%20Prototype-1f8f5f" />
</p>

---

## Overview

**NextDmarc** is a DMARC governance and monitoring frontend prototype designed for multi-role security operations.
It provides a clear, role-aware user experience for tracking compliance, triaging alerts, and managing email security posture.

The project is organized for future full-stack expansion:

- `frontend/` -> fully functional Next.js application
- `backend/` -> reserved for upcoming API/services implementation

---

## Key Features

- **Role-based access model** (NEXTSTEP Admin, Client Admin, Analyst SOC, Client User)
- **Operational dashboards** for visibility into compliance and threat indicators
- **Alert and reporting views** for SOC workflows
- **Bilingual interface support** (English/French switcher)
- **Professional design system** aligned with the NextStep visual theme

---

## Tech Stack

### Frontend (`frontend/`)
- **Framework:** Next.js 14 (Pages Router)
- **UI:** Material UI (MUI) + Tailwind CSS
- **Language:** JavaScript (React 18)
- **Linting:** ESLint (`next lint`)

### Backend (`backend/`)
- Placeholder folder (intentionally empty for now)

---

## Project Structure

```text
NextDmarc/
|-- frontend/
|   |-- src/
|   |   |-- access/         # RBAC config and route permissions
|   |   |-- components/     # Reusable UI and layout components
|   |   |-- data/           # Mock data (temporary)
|   |   |-- i18n/           # Language context and dictionaries
|   |   |-- pages/          # Next.js pages/routes
|   |   |-- styles/         # Global styles
|   |   `-- theme.js        # NextStep MUI theme tokens
|   |-- package.json
|   `-- ...
`-- backend/
    `-- .gitkeep
```

---

## Getting Started

### 1) Install dependencies

```bash
cd frontend
npm install
```

### 2) Run in development

```bash
npm run dev
```

### 3) Quality and production checks

```bash
npm run lint
npm run build
npm run start
```

---

## Role Model

The access model is defined in `frontend/src/access/roles.js`:

- `nextstep_admin`
- `client_admin`
- `analyst_soc`
- `client_user`

Each role has route-level permissions and a default landing page.

---

## Roadmap

- Connect frontend modules to real backend APIs
- Add authentication/session management beyond local mock login
- Introduce audit trails and tenant-level governance controls
- Expand observability and security analytics features

---

## Collaboration Notes

- Keep all UI development inside `frontend/`
- Keep `backend/` reserved for server-side work
- Avoid committing generated artifacts (`node_modules`, `.next`, logs)

---

## License

No open-source license has been declared yet.
If this project is intended for public distribution, add a `LICENSE` file.

