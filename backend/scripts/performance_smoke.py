from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from time import perf_counter

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app


@dataclass(slots=True)
class CaseResult:
    name: str
    method: str
    path: str
    expected_status: int
    latencies_ms: list[float]
    status_counts: dict[int, int]


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0

    sorted_values = sorted(values)
    rank = (len(sorted_values) - 1) * percentile
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = rank - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def _run_case(
    *,
    client: TestClient,
    name: str,
    method: str,
    path: str,
    expected_status: int,
    iterations: int,
) -> CaseResult:
    latencies_ms: list[float] = []
    status_counts: dict[int, int] = {}

    for _ in range(iterations):
        started = perf_counter()
        response = client.request(method=method, url=path)
        elapsed_ms = (perf_counter() - started) * 1000.0
        latencies_ms.append(elapsed_ms)
        status_counts[response.status_code] = status_counts.get(response.status_code, 0) + 1

    return CaseResult(
        name=name,
        method=method,
        path=path,
        expected_status=expected_status,
        latencies_ms=latencies_ms,
        status_counts=status_counts,
    )


def _format_case_row(result: CaseResult) -> str:
    expected_hits = result.status_counts.get(result.expected_status, 0)
    min_ms = min(result.latencies_ms) if result.latencies_ms else 0.0
    max_ms = max(result.latencies_ms) if result.latencies_ms else 0.0
    avg_ms = mean(result.latencies_ms) if result.latencies_ms else 0.0
    p95_ms = _percentile(result.latencies_ms, 0.95)
    p99_ms = _percentile(result.latencies_ms, 0.99)

    return (
        f"| {result.name} | {result.method} {result.path} | {result.expected_status} "
        f"| {expected_hits}/{len(result.latencies_ms)} | {avg_ms:.2f} | {p95_ms:.2f} "
        f"| {p99_ms:.2f} | {min_ms:.2f} | {max_ms:.2f} |"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run in-process performance smoke baseline.")
    parser.add_argument(
        "--iterations",
        type=int,
        default=250,
        help="Requests per endpoint.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="artifacts/performance-smoke-baseline-latest.md",
        help="Path to markdown output file relative to backend/.",
    )
    args = parser.parse_args()

    if args.iterations < 1:
        raise ValueError("iterations must be >= 1")

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    with TestClient(app) as client:
        results = [
            _run_case(
                client=client,
                name="Root",
                method="GET",
                path="/",
                expected_status=200,
                iterations=args.iterations,
            ),
            _run_case(
                client=client,
                name="Health",
                method="GET",
                path="/health",
                expected_status=200,
                iterations=args.iterations,
            ),
            _run_case(
                client=client,
                name="Metrics",
                method="GET",
                path="/metrics",
                expected_status=200,
                iterations=args.iterations,
            ),
        ]

    failed = [
        result.name
        for result in results
        if result.status_counts.get(result.expected_status, 0) == 0
    ]

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = Path(__file__).resolve().parents[1] / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now(tz=UTC).isoformat()
    lines = [
        "# Performance Smoke Baseline",
        "",
        f"- Generated: {generated_at}",
        "- Mode: in-process FastAPI TestClient benchmark",
        f"- Iterations per endpoint: {args.iterations}",
        "",
        "| Endpoint | Request | Expected | Successes | Avg ms | P95 ms | P99 ms | Min ms | Max ms |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    lines.extend(_format_case_row(result) for result in results)

    if failed:
        lines.extend(
            [
                "",
                "## Result",
                f"- FAILED: expected status not observed for {', '.join(failed)}",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "## Result",
                "- PASS: expected status observed for all smoke endpoints.",
            ]
        )

    output_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Performance smoke report written to: {output_path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
