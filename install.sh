#!/bin/bash

set -e

PLUGIN_NAME="TPLinkRouter"
DOMOTICZ_DIR="${DOMOTICZ_DIR:-/home/pi/domoticz}"
PLUGIN_DIR="$DOMOTICZ_DIR/plugins/$PLUGIN_NAME"
CURRENT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PLUGIN_DIR/venv"

echo "======================================"
echo " TP-Link Router Domoticz Plugin Setup "
echo "======================================"
echo ""

if [ ! -f "$CURRENT_DIR/plugin.py" ]; then
    echo "ERROR: plugin.py was not found."
    echo "Run install.sh from the plugin repository directory."
    exit 1
fi

if [ ! -f "$CURRENT_DIR/requirements.txt" ]; then
    echo "ERROR: requirements.txt was not found."
    echo "Run install.sh from the plugin repository directory."
    exit 1
fi

if [ ! -d "$DOMOTICZ_DIR" ]; then
    echo "ERROR: Domoticz directory not found: $DOMOTICZ_DIR"
    echo ""
    echo "If Domoticz is installed elsewhere, run:"
    echo "  DOMOTICZ_DIR=/path/to/domoticz ./install.sh"
    exit 1
fi

echo "Domoticz directory: $DOMOTICZ_DIR"
echo "Plugin directory:   $PLUGIN_DIR"
echo "Virtualenv:         $VENV_DIR"
echo ""

echo "[1/8] Installing required system packages..."
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git

echo "[2/8] Checking Python version..."
PYTHON_OK="$(python3 - <<'PY'
import sys
print("yes" if sys.version_info >= (3, 8) else "no")
PY
)"

PYTHON_VERSION="$(python3 - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
PY
)"

if [ "$PYTHON_OK" != "yes" ]; then
    echo "ERROR: Python 3.8 or newer is required. Found Python $PYTHON_VERSION"
    exit 1
fi

echo "Python version OK: $PYTHON_VERSION"

echo "[3/8] Creating plugin directory..."
mkdir -p "$PLUGIN_DIR"

echo "[4/8] Copying plugin files..."
cp "$CURRENT_DIR/plugin.py" "$PLUGIN_DIR/plugin.py"
cp "$CURRENT_DIR/requirements.txt" "$PLUGIN_DIR/requirements.txt"

if [ -f "$CURRENT_DIR/README.md" ]; then
    cp "$CURRENT_DIR/README.md" "$PLUGIN_DIR/README.md"
fi

if [ -f "$CURRENT_DIR/LICENSE" ]; then
    cp "$CURRENT_DIR/LICENSE" "$PLUGIN_DIR/LICENSE"
fi

if [ -f "$CURRENT_DIR/CHANGELOG.md" ]; then
    cp "$CURRENT_DIR/CHANGELOG.md" "$PLUGIN_DIR/CHANGELOG.md"
fi

echo "[5/8] Creating isolated Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
else
    echo "Virtualenv already exists, reusing it."
fi

echo "[6/8] Installing Python dependencies into virtualenv..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$PLUGIN_DIR/requirements.txt"

echo "[7/8] Verifying Python dependencies..."
"$VENV_DIR/bin/python" - <<'PY'
import tplinkrouterc6u
import urllib3
import requests
import Crypto
print("Dependencies OK")
PY

echo "[8/8] Checking plugin syntax..."
python3 -m py_compile "$PLUGIN_DIR/plugin.py"

echo ""
echo "Restarting Domoticz..."
if command -v systemctl >/dev/null 2>&1; then
    if systemctl list-unit-files | grep -q '^domoticz\.service'; then
        sudo systemctl restart domoticz || {
            echo "WARNING: Could not restart Domoticz automatically. Please restart it manually."
        }
    else
        echo "WARNING: domoticz.service was not found. Please restart Domoticz manually."
    fi
else
    echo "WARNING: systemctl not found. Please restart Domoticz manually."
fi

echo ""
echo "======================================"
echo " TP-Link Router Plugin installed OK"
echo " Python ...... OK"
echo " Virtualenv .. OK"
echo " Dependencies  OK"
echo " Plugin syntax OK"
echo "======================================"
echo ""
echo "Next step:"
echo "  Domoticz -> Setup -> Hardware -> Add: TP-Link Router"
echo ""
echo "Recommended settings:"
echo "  Scheme: HTTPS"
echo "  Verify SSL: False"
echo "  Poll interval: 180"
