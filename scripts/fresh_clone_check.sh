
#!/usr/bin/env bash
set -euo pipefail

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

git clone "$(git remote get-url origin)" "$tmp/repo"
cd "$tmp/repo"

# Select the available Python launcher.
if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON=python
elif command -v py >/dev/null 2>&1; then
    PYTHON=py
else
    echo "ERROR: Python 3 was not found."
    exit 1
fi

# Create and activate a clean virtual environment.
"$PYTHON" -m venv .venv

if [ -f .venv/Scripts/activate ]; then
    source .venv/Scripts/activate
else
    source .venv/bin/activate
fi

python -m pip install --upgrade pip
python -m pip install -e ".[dev,ui]"

ruff check .
pytest -q
python scripts/validate_gold.py
python scripts/ci_eval.py

copilot --help >/dev/null
echo "FRESH CLONE OK"
