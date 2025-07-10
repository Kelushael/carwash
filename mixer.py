import json
import re
from pathlib import Path

import click
from pydub import AudioSegment
import pyloudnorm as pyln


@click.group()
def cli():
    """Car Wash Mixer CLI."""
    pass


@cli.command()
@click.option("--input", "infile", required=True, type=click.Path(exists=True), help="Input audio file")
@click.option("--output", "outfile", required=True, type=click.Path(), help="Output cleaned file")
@click.option("--preset", default="car-wash", help="Mix preset (unused)")
def mix(infile: str, outfile: str, preset: str):
    """Normalize loudness to -14 LUFS and export."""
    audio = AudioSegment.from_file(infile)
    meter = pyln.Meter(audio.frame_rate)
    samples = audio.get_array_of_samples()
    loudness = meter.integrated_loudness(samples)
    normalized = pyln.normalize.loudness(samples, loudness, -14.0)
    cleaned = AudioSegment(
        data=normalized.tobytes(),
        sample_width=audio.sample_width,
        frame_rate=audio.frame_rate,
        channels=audio.channels,
    )
    cleaned.export(outfile, format=Path(outfile).suffix.lstrip("."))
    click.echo(f"Done. Loudness was {loudness:.2f} LUFS, now -14 LUFS.")


@cli.command()
@click.option("--lyrics", "lyrics_path", required=True, type=click.Path(exists=True), help="Input LRC file")
@click.option("--bpm", type=float, required=True, help="Beats per minute")
@click.option("--beats-per-bar", default=4, type=int, show_default=True, help="Beats per bar")
@click.option("--offset", default=0.0, type=float, show_default=True, help="Seconds offset before first beat")
@click.option("--output", "output_json", required=True, type=click.Path(), help="Output JSON file")
def map_lyrics(lyrics_path: str, bpm: float, beats_per_bar: int, offset: float, output_json: str):
    """Convert LRC lyrics to a JSON mapping keyed by bar and timestamp."""
    beat_duration = 60.0 / bpm
    bar_duration = beat_duration * beats_per_bar
    mapping = {}

    timestamp_pattern = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")
    with open(lyrics_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            match = timestamp_pattern.match(line)
            if not match:
                continue
            minutes = int(match.group(1))
            seconds = float(match.group(2))
            text = line[match.end():].strip()
            ts = minutes * 60 + seconds
            bar_index = int((ts - offset) / bar_duration) + 1
            key = f"bar_{bar_index}_{ts:.2f}"
            mapping[key] = text

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2)
    click.echo(f"Wrote {len(mapping)} mappings to {output_json}")


if __name__ == "__main__":
    cli()
