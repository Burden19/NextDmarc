# NextDmarc Frontend - Explanation

## Purpose
This folder provides a UI foundation for the NextDmarc platform. It is aligned with the conception package for the four-actor model and focuses on SOC-friendly workflows: collection, parsing, detection, scoring, recommendations, and alerting.

## Roles and Responsibilities
- NEXTSTEP Admin: full control of platform configuration, tenant creation, global policies, and security.
- Client Admin: manages domains, DMARC policies, onboarding, and integration setups.
- Analyst SOC: monitors alerts, investigates anomalies, and manages incident response actions.
- Client User: consumes dashboards, compliance reports, and risk summaries.

## Role Relationships
- NEXTSTEP Admin governs the platform and delegates access to Client Admins.
- Client Admin grants access to Client Users and collaborates with Analyst SOC on incident response.
- Analyst SOC reviews alerts and shares remediation outcomes with Client Admins.
- Client Users are read-focused and rely on Admin roles for policy changes.

## Pages and Mapping
- `index.js`: overview with metrics and role summary; acts as landing.
- `dashboard.js`: SOC dashboard with compliance trend and alert queue.
- `domains.js`: domain portfolio, policy status, compliance levels.
- `reports.js`: RUA processing pipeline, parsing, normalization status.
- `alerts.js`: active alerts and guidance for triage.
- `scoring.js`: risk scoring by source, threat intelligence context.
- `recommendations.js`: DMARC maturity improvements and action list.
- `integrations.js`: SIEM/SOAR, ChatOps, webhook and API exposure.
- `governance.js`: multi-tenant controls and role privileges.
- `settings.js`: ingestion, retention, and alert thresholds.

## UI Components
- `AppLayout`: top bar + sidebar layout for all pages.
- `TopBar`: product identity and role indicator.
- `SideNav`: navigation aligned with the use-case packages.
- `StatCard`, `SectionCard`, `DataTable`, `AlertList`: building blocks for dashboards.

## How It Connects to the Conception
- The navigation mirrors the major use-case packages (collection, analysis, scoring, governance, integrations, visualization).
- The metrics and tables are placeholders for the backend services defined in the deployment diagram.
- The governance page enforces the four-actor model.

## Next Steps
- Replace `src/data/mock.js` with API calls.
- Add authentication flows and role switching.
- Implement real charts (e.g., Recharts, ECharts).

