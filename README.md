# Car Wash Mixer

A minimal CLI for audio cleanup and lyric mapping.

## Setup

```bash
./setup.sh
```

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Clean an audio track:

```bash
wash-mix mix --input song.wav --output cleaned.wav
```

Create a lyrics mapping (from an LRC file):

```bash
wash-mix map-lyrics --lyrics song.lrc --bpm 120 --output mapping.json
```

The mapping JSON keys combine bar numbers and timestamps for easy reference.

## API and Custom GPT

You can run a small Flask server exposing these features as a ChatGPT
plugin:

```bash
python server.py
```

The `ai-plugin.json` and `openapi.json` files describe the available
endpoints so you can create a custom GPT that calls the `/mix` and
`/map-lyrics` routes directly.
