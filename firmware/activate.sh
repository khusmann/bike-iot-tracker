#!/bin/bash

# Create venv if missing
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt -q --disable-pip-version-check

echo "Virtual environment ready and activated."