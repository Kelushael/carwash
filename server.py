from flask import Flask, jsonify, request, send_file
from pathlib import Path

from mixer import mix_audio, map_lyrics_file

app = Flask(__name__)


@app.route("/mix", methods=["POST"])
def mix_endpoint():
    data = request.get_json(force=True)
    infile = data["input"]
    outfile = data["output"]
    preset = data.get("preset", "car-wash")
    loudness = mix_audio(infile, outfile, preset)
    return jsonify({"message": f"Normalized to -14 LUFS", "original_loudness": loudness})


@app.route("/map-lyrics", methods=["POST"])
def map_lyrics_endpoint():
    data = request.get_json(force=True)
    lyrics = data["lyrics"]
    bpm = float(data["bpm"])
    beats_per_bar = int(data.get("beats_per_bar", 4))
    offset = float(data.get("offset", 0.0))
    output = data["output"]
    mapping = map_lyrics_file(lyrics, bpm, beats_per_bar, offset, output)
    return jsonify({"message": f"Wrote {len(mapping)} mappings", "count": len(mapping)})


@app.route("/openapi.json")
def openapi_spec():
    return send_file(Path(__file__).with_name("openapi.json"))


@app.route("/.well-known/ai-plugin.json")
def plugin_manifest():
    """Serve the plugin manifest for ChatGPT."""
    return send_file(Path(__file__).with_name("ai-plugin.json"))


@app.route("/privacy")
def privacy_policy():
    """Serve the privacy policy markdown file."""
    return send_file(Path(__file__).with_name("PRIVACY.md"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
