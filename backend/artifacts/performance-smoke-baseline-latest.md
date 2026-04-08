# Performance Smoke Baseline

- Generated: 2026-04-07T16:12:16.425948+00:00
- Mode: in-process FastAPI TestClient benchmark
- Iterations per endpoint: 250

| Endpoint | Request | Expected | Successes | Avg ms | P95 ms | P99 ms | Min ms | Max ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Root | GET / | 200 | 250/250 | 2.16 | 3.02 | 3.45 | 1.29 | 3.80 |
| Health | GET /health | 200 | 250/250 | 1.77 | 2.52 | 2.88 | 1.07 | 3.00 |
| Metrics | GET /metrics | 200 | 250/250 | 3.14 | 4.23 | 4.69 | 2.02 | 4.88 |

## Result
- PASS: expected status observed for all smoke endpoints.