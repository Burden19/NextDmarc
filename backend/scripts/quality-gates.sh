#!/usr/bin/env bash
set -euo pipefail

SKIP_AUDIT="${SKIP_AUDIT:-0}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_PYTHON="$SCRIPT_DIR/../../.venv/bin/python"

if command -v uv >/dev/null 2>&1; then
  RUNNER="uv"
elif [[ -x "$WORKSPACE_PYTHON" ]]; then
  RUNNER="$WORKSPACE_PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  RUNNER="python3"
elif command -v python >/dev/null 2>&1; then
  RUNNER="python"
else
  echo "Neither uv nor python interpreter found."
  exit 1
fi

run_quality_tool() {
  if [[ "$RUNNER" == "uv" ]]; then
    uv run "$@"
  else
    "$RUNNER" -m "$@"
  fi
}

run_pip_audit() {
  if [[ "$RUNNER" == "uv" ]]; then
    uv run pip-audit "$@"
  else
    "$RUNNER" -m pip_audit "$@"
  fi
}

HAS_PYTHON_SOURCES=0
if find app tests scripts -type f -name '*.py' 2>/dev/null | grep -q .; then
  HAS_PYTHON_SOURCES=1
fi

echo "[1/5] Ruff lint + format check"
if [[ "$HAS_PYTHON_SOURCES" == "1" ]]; then
  run_quality_tool ruff check app tests scripts
  run_quality_tool ruff format --check app tests scripts
else
  echo "No Python files found; skipping Ruff checks."
fi

echo "[2/5] Mypy strict"
if [[ "$HAS_PYTHON_SOURCES" == "1" ]]; then
  run_quality_tool mypy --strict app
else
  echo "No Python files found; skipping Mypy."
fi

echo "[3/5] Bandit security scan"
if [[ "$HAS_PYTHON_SOURCES" == "1" ]]; then
  run_quality_tool bandit -r app -c pyproject.toml
else
  echo "No Python files found; skipping Bandit."
fi

if [[ "$SKIP_AUDIT" != "1" ]]; then
  echo "[4/5] pip-audit dependency scan"
  run_pip_audit --ignore-vuln CVE-2024-23342 --ignore-vuln CVE-2026-4539
else
  echo "[4/5] pip-audit skipped"
fi

echo "[5/5] Pytest with coverage"
if [[ "$HAS_PYTHON_SOURCES" == "1" ]]; then
  run_quality_tool pytest
else
  echo "No Python files found; skipping Pytest."
fi

echo "All quality gates passed."
