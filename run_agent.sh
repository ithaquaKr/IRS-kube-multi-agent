#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Check if uv is installed
if ! command -v uv &>/dev/null; then
    echo "uv could not be found, please install it: pip install uv"
    exit 1
fi

echo "Installing dependencies..."
uv pip install -e .

echo "Starting the IRS-Kube-Multi-Agent system (FastAPI webhook and agent workflow)..."
python agents/__main__.py serve
