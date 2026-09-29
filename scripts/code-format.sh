#!/bin/bash

set -e

poetry run black -t py310 -l 88 shutil_mcp tests

# Remove trailing whitespace in project .py files
OS_NAME=$(uname -s)
case "$OS_NAME" in
  Darwin*|*BSD*)
    if sed --version 2>&1 | grep -q GNU; then
      find shutil_mcp tests -name "*.py" -exec sed -i 's/[[:space:]]*$//' {} +
    else
      find shutil_mcp tests -name "*.py" -exec sed -i '' 's/[[:space:]]*$//' {} +
    fi
    ;;
  *)
    find shutil_mcp tests -name "*.py" -exec sed -i 's/[[:space:]]*$//' {} +
    ;;
esac
