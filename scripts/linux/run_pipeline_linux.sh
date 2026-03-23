#!/bin/bash
# Linux-compatible pipeline runner

set -e

# Resolve project root from the script location.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON_BIN="venv/bin/python"

echo "========================================="
echo "Pharmaceutical News Agent Pipeline"
echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================="

$PYTHON_BIN src/run_pipeline.py

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "Pipeline completed successfully!"
else
    echo ""
    echo "Pipeline failed with exit code: $EXIT_CODE"
fi

exit $EXIT_CODE
