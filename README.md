# Car Wash Mixer

A professional audio toolkit featuring:
- CLI for audio cleanup and lyric mapping
- Professional AI-powered stem separator (vocals, drums, bass, instruments)

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

## Professional Stem Mixer (GUI)

Launch the AI-powered stem separator with a professional mixing interface:

```bash
python3 stem_mixer.py
```

Features:
- **AI-Powered Separation**: Uses Demucs (Facebook Research) for studio-quality stem separation
- **4-Stem Output**: Vocals, Drums, Bass, Other (guitar, piano, synths, etc.)
- **Professional Mixer**: Individual volume controls, solo/mute buttons for each stem
- **Real-time Preview**: Mix and preview before exporting
- **Flexible Export**: Export individual stems or custom mixes with your settings

Requirements:
- Python 3.8+
- FFmpeg (for audio processing)
- At least 4GB RAM (8GB recommended for longer tracks)

First-time use will download the Demucs AI model (~300MB).

## API and Custom GPT

You can run a small Flask server exposing these features as a ChatGPT
plugin:

```bash
python server.py
```

The `ai-plugin.json` and `openapi.json` files describe the available
endpoints so you can create a custom GPT that calls the `/mix` and
`/map-lyrics` routes directly.

Import the plugin using the following manifest URL once the server is
running:

```
http://localhost:5000/.well-known/ai-plugin.json
```

The privacy policy can be viewed at:

```
http://localhost:5000/privacy
```
