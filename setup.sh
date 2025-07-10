#!/usr/bin/env bash
set -e

if command -v apt >/dev/null 2>&1; then
  sudo apt update
  sudo apt install -y ffmpeg libsndfile1
elif command -v brew >/dev/null 2>&1; then
  brew install ffmpeg libsndfile
else
  echo "Install ffmpeg and libsndfile manually" >&2
fi

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Done. Activate with: source .venv/bin/activate"
