#!/usr/bin/env python3
"""
Offline TTS for the daily briefing podcast.

Uses espeak-ng (fully offline, no network, no API key) rather than a hosted
TTS API — this pipeline runs in a sandboxed cloud workspace whose egress
policy only allows GitHub/pypi/npm, so no external TTS provider (Noiz,
ElevenLabs, OpenAI, Edge TTS, Google TTS) is reachable at runtime.

Usage: python3 tts.py <script.txt> <output.mp3> [--voice en-us] [--speed 165] [--pitch 48]
"""
import argparse
import subprocess
import sys
import tempfile
import os


def synthesize(text: str, out_mp3: str, voice: str = "en-us", speed: int = 165, pitch: int = 48):
    with tempfile.TemporaryDirectory() as td:
        wav_path = os.path.join(td, "out.wav")
        txt_path = os.path.join(td, "in.txt")
        with open(txt_path, "w") as tf:
            tf.write(text)
        cmd = [
            "espeak-ng",
            "-v", voice,
            "-s", str(speed),
            "-p", str(pitch),
            "-g", "8",   # slight word gap for clarity
            "-f", txt_path,
            "-w", wav_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            print(proc.stderr, file=sys.stderr)
            sys.exit(1)

        # Encode to mp3, normalize loudness a bit for consistency across episodes.
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", wav_path,
            "-filter:a", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-codec:a", "libmp3lame", "-b:a", "128k", "-ar", "44100",
            out_mp3,
        ]
        proc2 = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if proc2.returncode != 0:
            print(proc2.stderr, file=sys.stderr)
            sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script_file")
    ap.add_argument("out_mp3")
    ap.add_argument("--voice", default="en-us")
    ap.add_argument("--speed", type=int, default=165)
    ap.add_argument("--pitch", type=int, default=48)
    args = ap.parse_args()

    with open(args.script_file) as f:
        text = f.read()

    synthesize(text, args.out_mp3, args.voice, args.speed, args.pitch)
    print(f"Wrote {args.out_mp3}")


if __name__ == "__main__":
    main()
