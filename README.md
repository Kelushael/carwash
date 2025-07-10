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
