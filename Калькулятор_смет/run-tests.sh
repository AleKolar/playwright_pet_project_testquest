#!/bin/bash
set -e

cd "$(dirname "$0")"

PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python not found"
    exit 1
fi

echo "Using Python: $PYTHON_CMD"

$PYTHON_CMD -m pip install --upgrade pip --break-system-packages
$PYTHON_CMD -m pip install -r requirements.txt --break-system-packages

$PYTHON_CMD -m playwright install chromium

export BASE_URL=${BASE_URL:-https://testquest.pryaniky.com}
$PYTHON_CMD -m pytest tests/ -v --tb=short --maxfail=5

exit $?