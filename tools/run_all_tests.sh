#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python_bin="${PYTHON_BIN:-$repo_root/.venv/bin/python}"

"$python_bin" -m pytest -q
"$python_bin" -m pytest -q tests/webdashboard/e2e --browser chromium

cd "$repo_root/webdashboard/frontend"
npm test -- --reporter=line
