#!/usr/bin/env bash
# One-command setup for Pose-Controlled AI Arcade (macOS/Linux).
#
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
#
# What this does:
#   1. Finds a working Python 3.11 interpreter
#   2. Creates a virtual environment in ./venv (skips if it already exists)
#   3. Installs the pinned dependencies from requirements.txt
#   4. Launches the game
#
# Re-running this later just reuses the existing venv and launches the game
# again — safe to run any time.

set -e

echo "=== Pose-Controlled AI Arcade — Setup ==="

# --- Find Python 3.11 ---
PYTHON_BIN=""
for candidate in python3.11 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        version=$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "")
        if [ "$version" = "3.11" ]; then
            PYTHON_BIN="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo ""
    echo "ERROR: Could not find a Python 3.11 interpreter on this machine."
    echo "MediaPipe does not reliably support newer Python versions (3.12+)."
    echo ""
    echo "Install Python 3.11 first:"
    echo "  macOS:  brew install python@3.11"
    echo "  Linux:  use your distro's package manager (e.g. apt install python3.11)"
    echo ""
    echo "Then run ./setup.sh again."
    exit 1
fi

echo "Using: $PYTHON_BIN ($($PYTHON_BIN --version))"

# --- Create venv if it doesn't already exist ---
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    "$PYTHON_BIN" -m venv venv
else
    echo "Virtual environment already exists — reusing it."
fi

# shellcheck disable=SC1091
source venv/bin/activate

echo "Installing dependencies (this can take a few minutes the first time)..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "=== Setup complete. Launching the game... ==="
echo ""

python3 main.py
