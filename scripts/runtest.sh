#!/bin/bash

CPU_CORES=$(lscpu | awk '/^Core\(s\) per socket:/ {c=$4} /^Socket\(s\):/ {s=$2} END {print c * s}')

# cleanup
rm -rf */__pycache__ .pytest_cache .coverage

# update existing packages as defined on pyproject.toml
poetry update

# install current project as editable
pip install -q -e .[speed]

# regenerate poetry.lock based on installed/updated packages
rm -f poetry.lock && poetry lock --no-cache

# run unit tests
PYTHONPATH=. poetry run pytest tests/ -n $CPU_CORES --cov=shutil_mcp --cov-report=term-missing --cov-fail-under=40
