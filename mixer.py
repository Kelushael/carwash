import json
import re
import gc
import logging
from pathlib import Path
from typing import Dict, Optional

import click
from pydub import AudioSegment
import pyloudnorm as pyln
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Car Wash Mixer CLI."""
    pass


def mix_audio(infile: str, outfile: str, preset: str = "car-wash") -> float:
    """Normalize loudness to -14 LUFS and export with optimized memory usage.

    Returns the original loudness of the file.
    """
    try:
        logger.info(f"Loading audio file: {infile}")
        
        # Load audio with error handling
        audio = AudioSegment.from_file(infile)
        
        # Check audio properties
        if audio.frame_rate < 8000 or audio.frame_rate > 192000:
            raise ValueError(f"Unsupported sample rate: {audio.frame_rate}")
        
        if len(audio) == 0:
            raise ValueError("Audio file is empty")
        
        # Create meter for loudness measurement
        meter = pyln.Meter(audio.frame_rate)
        
        # Convert to numpy array more efficiently
        samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
        
        # Handle stereo audio
        if audio.channels == 2:
            samples = samples.reshape((-1, 2))
        
        # Measure integrated loudness
        logger.info("Measuring loudness...")
        loudness = meter.integrated_loudness(samples)
        
        # Normalize to -14 LUFS
        logger.info(f"Original loudness: {loudness:.2f} LUFS, normalizing to -14 LUFS")
        normalized = pyln.normalize.loudness(samples, loudness, -14.0)
        
        # Convert back to appropriate data type
        normalized_int = (normalized * 32767).astype(np.int16)
        
        # Create new AudioSegment with normalized data
        cleaned = AudioSegment(
            data=normalized_int.tobytes(),
            sample_width=audio.sample_width,
            frame_rate=audio.frame_rate,
            channels=audio.channels,
        )
        
        # Export with optimized format detection
        output_path = Path(outfile)
        output_format = output_path.suffix.lstrip(".").lower()
        
        # Optimize export parameters based on format
        export_params = {}
        if output_format == "mp3":
            export_params["bitrate"] = "192k"
        elif output_format == "wav":
            export_params["parameters"] = ["-acodec", "pcm_s16le"]
        
        logger.info(f"Exporting to {outfile} (format: {output_format})")
        cleaned.export(outfile, format=output_format, **export_params)
        
        # Clean up memory
        del audio, samples, normalized, normalized_int, cleaned
        gc.collect()
        
        logger.info("Audio processing completed successfully")
        return float(loudness)
        
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        raise


@cli.command()
@click.option("--input", "infile", required=True, type=click.Path(exists=True), help="Input audio file")
@click.option("--output", "outfile", required=True, type=click.Path(), help="Output cleaned file")
@click.option("--preset", default="car-wash", help="Mix preset (unused)")
def mix(infile: str, outfile: str, preset: str):
    """CLI wrapper for :func:`mix_audio`."""
    try:
        loudness = mix_audio(infile, outfile, preset)
        click.echo(f"Done. Loudness was {loudness:.2f} LUFS, now -14 LUFS.")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


def map_lyrics_file(
    lyrics_path: str,
    bpm: float,
    beats_per_bar: int = 4,
    offset: float = 0.0,
    output_json: Optional[str] = None,
) -> Dict[str, str]:
    """Convert LRC lyrics to a mapping keyed by bar and timestamp with optimized processing."""
    try:
        # Validate inputs
        if bpm <= 0:
            raise ValueError("BPM must be positive")
        if beats_per_bar <= 0:
            raise ValueError("Beats per bar must be positive")
        
        beat_duration = 60.0 / bpm
        bar_duration = beat_duration * beats_per_bar
        mapping: Dict[str, str] = {}

        # Compile regex pattern once for better performance
        timestamp_pattern = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")
        
        logger.info(f"Processing lyrics file: {lyrics_path}")
        
        # Read file with better encoding handling
        try:
            with open(lyrics_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            # Fallback to other encodings
            with open(lyrics_path, "r", encoding="latin-1") as f:
                lines = f.readlines()
        
        processed_lines = 0
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
                
            match = timestamp_pattern.match(line)
            if not match:
                continue
                
            try:
                minutes = int(match.group(1))
                seconds = float(match.group(2))
                text = line[match.end():].strip()
                
                # Skip empty text entries
                if not text:
                    continue
                
                ts = minutes * 60 + seconds
                bar_index = int((ts - offset) / bar_duration) + 1
                
                # Create more descriptive key format
                key = f"bar_{bar_index:04d}_{ts:.3f}"
                mapping[key] = text
                processed_lines += 1
                
            except (ValueError, IndexError) as e:
                logger.warning(f"Skipping invalid line {line_num}: {line} ({e})")
                continue

        logger.info(f"Processed {processed_lines} lyrics entries")
        
        # Save to JSON with better formatting
        if output_json:
            output_path = Path(output_json)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_json, "w", encoding="utf-8") as f:
                json.dump(mapping, f, indent=2, ensure_ascii=False, sort_keys=True)
            
            logger.info(f"Saved {len(mapping)} mappings to {output_json}")

        return mapping
        
    except Exception as e:
        logger.error(f"Error processing lyrics: {e}")
        raise


@cli.command()
@click.option("--lyrics", "lyrics_path", required=True, type=click.Path(exists=True), help="Input LRC file")
@click.option("--bpm", type=float, required=True, help="Beats per minute")
@click.option("--beats-per-bar", default=4, type=int, show_default=True, help="Beats per bar")
@click.option("--offset", default=0.0, type=float, show_default=True, help="Seconds offset before first beat")
@click.option("--output", "output_json", required=True, type=click.Path(), help="Output JSON file")
def map_lyrics(lyrics_path: str, bpm: float, beats_per_bar: int, offset: float, output_json: str):
    """CLI wrapper for :func:`map_lyrics_file`."""
    try:
        mapping = map_lyrics_file(lyrics_path, bpm, beats_per_bar, offset, output_json)
        click.echo(f"Wrote {len(mapping)} mappings to {output_json}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
