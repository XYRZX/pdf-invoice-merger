#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3}"
APP_NAME="InvoiceMerge"

if [ ! -d ".venv" ]; then
  $PYTHON_BIN -m venv .venv
fi

source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt

rm -rf dist build

export PYINSTALLER_CONFIG_DIR="$PWD/.pyinstaller"
rm -rf "$PYINSTALLER_CONFIG_DIR"
mkdir -p "$PYINSTALLER_CONFIG_DIR"

pyinstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "$APP_NAME" \
  app/main.py

if [ -f packaging/dmgbuild_settings.py ]; then
  pip install dmgbuild
  rm -f "dist/${APP_NAME}.dmg"
  if [ -d "dist/${APP_NAME}.app" ]; then
    dmgbuild \
      -s packaging/dmgbuild_settings.py \
      -D "app=dist/${APP_NAME}.app" \
      -D "appname=${APP_NAME}" \
      "$APP_NAME" \
      "dist/${APP_NAME}.dmg"
  fi
fi

open dist
