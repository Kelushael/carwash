import os
import hashlib
import json
from flask import Flask, jsonify, request, send_file
from flask_compress import Compress
from pathlib import Path
import redis
import logging

from mixer import mix_audio, map_lyrics_file

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Enable gzip compression for all responses
Compress(app)

# Configure Redis for caching (with fallback if Redis unavailable)
try:
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=0,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    redis_client.ping()
    REDIS_AVAILABLE = True
    logger.info("Redis connection established")
except (redis.ConnectionError, redis.TimeoutError):
    redis_client = None
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, running without cache")

# Cache TTL in seconds (1 hour)
CACHE_TTL = 3600


def get_cache_key(operation: str, **kwargs) -> str:
    """Generate a cache key based on operation and parameters."""
    data = f"{operation}:{json.dumps(kwargs, sort_keys=True)}"
    return hashlib.md5(data.encode()).hexdigest()


def get_from_cache(key: str):
    """Get value from cache if available."""
    if not REDIS_AVAILABLE:
        return None
    try:
        return redis_client.get(key)
    except redis.RedisError:
        logger.warning("Cache read error")
        return None


def set_cache(key: str, value: str):
    """Set value in cache if available."""
    if not REDIS_AVAILABLE:
        return
    try:
        redis_client.setex(key, CACHE_TTL, value)
    except redis.RedisError:
        logger.warning("Cache write error")


@app.errorhandler(400)
def bad_request(error):
    """Handle bad requests."""
    return jsonify({"error": "Bad request", "message": str(error)}), 400


@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    logger.error(f"Internal error: {error}")
    return jsonify({"error": "Internal server error"}), 500


@app.route("/mix", methods=["POST"])
def mix_endpoint():
    try:
        data = request.get_json(force=True)
        
        # Validate required fields
        if not data or "input" not in data or "output" not in data:
            return jsonify({"error": "Missing required fields: input, output"}), 400
        
        infile = data["input"]
        outfile = data["output"]
        preset = data.get("preset", "car-wash")
        
        # Validate file paths
        if not Path(infile).exists():
            return jsonify({"error": f"Input file not found: {infile}"}), 400
        
        # Check cache
        cache_key = get_cache_key("mix", input=infile, preset=preset)
        cached_result = get_from_cache(cache_key)
        if cached_result:
            logger.info(f"Cache hit for mix operation: {cache_key}")
            return jsonify(json.loads(cached_result))
        
        # Process audio
        logger.info(f"Processing audio: {infile} -> {outfile}")
        loudness = mix_audio(infile, outfile, preset)
        
        result = {
            "message": "Normalized to -14 LUFS",
            "original_loudness": loudness,
            "preset": preset
        }
        
        # Cache result
        set_cache(cache_key, json.dumps(result))
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in mix endpoint: {e}")
        return jsonify({"error": "Processing failed", "message": str(e)}), 500


@app.route("/map-lyrics", methods=["POST"])
def map_lyrics_endpoint():
    try:
        data = request.get_json(force=True)
        
        # Validate required fields
        required_fields = ["lyrics", "bpm", "output"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
        
        lyrics = data["lyrics"]
        bpm = float(data["bpm"])
        beats_per_bar = int(data.get("beats_per_bar", 4))
        offset = float(data.get("offset", 0.0))
        output = data["output"]
        
        # Validate file paths
        if not Path(lyrics).exists():
            return jsonify({"error": f"Lyrics file not found: {lyrics}"}), 400
        
        # Validate BPM
        if bpm <= 0:
            return jsonify({"error": "BPM must be positive"}), 400
        
        # Check cache
        cache_key = get_cache_key("map_lyrics", lyrics=lyrics, bpm=bpm, beats_per_bar=beats_per_bar, offset=offset)
        cached_result = get_from_cache(cache_key)
        if cached_result:
            logger.info(f"Cache hit for map_lyrics operation: {cache_key}")
            return jsonify(json.loads(cached_result))
        
        # Process lyrics
        logger.info(f"Processing lyrics: {lyrics} -> {output}")
        mapping = map_lyrics_file(lyrics, bpm, beats_per_bar, offset, output)
        
        result = {
            "message": f"Wrote {len(mapping)} mappings",
            "count": len(mapping),
            "bpm": bpm,
            "beats_per_bar": beats_per_bar,
            "offset": offset
        }
        
        # Cache result
        set_cache(cache_key, json.dumps(result))
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({"error": "Invalid input", "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Error in map_lyrics endpoint: {e}")
        return jsonify({"error": "Processing failed", "message": str(e)}), 500


@app.route("/health")
def health_check():
    """Health check endpoint for load balancers."""
    status = {
        "status": "healthy",
        "cache_available": REDIS_AVAILABLE
    }
    return jsonify(status)


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
    # Development server (not for production)
    app.run(host="0.0.0.0", port=5000, debug=False)
