#!/usr/bin/env python3
"""Re-voice daily briefing episodes with Kokoro TTS (runs in GitHub Actions).

Usage: python tools/kokoro_render.py pipeline/scripts/2026-10-08.txt [...]

For each script: renders Kokoro audio, overwrites 94e35a148cb16749/episodes/<date>.mp3,
updates that episode's size_bytes / duration / voice in episodes_manifest.json, then
rebuilds feed.xml with generate_feed.py. The espeak-ng episode published by the
daily cloud task stays untouched if anything here fails.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline

VOICE = os.environ.get("KOKORO_VOICE", "af_heart")
SPEED = float(os.environ.get("KOKORO_SPEED", "1.0"))
FEED_DIR = Path(os.environ.get("FEED_DIR", "94e35a148cb16749"))
BASE_URL = os.environ.get(
    "FEED_BASE_URL",
    "https://shanegalligan1-bit.github.io/briefing-94e35a14/94e35a148cb16749",
)
SR = 24000
PAUSE = np.zeros(int(SR * 0.6), dtype=np.float32)

_pipe = None


def pipeline():
    global _pipe
    if _pipe is None:
        _pipe = KPipeline(lang_code=VOICE[0])  # 'a' US English, 'b' British
    return _pipe


def render(text: str, out_mp3: Path) -> None:
    chunks = []
    for para in [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]:
        for _, _, audio in pipeline()(para, voice=VOICE, speed=SPEED):
            if audio is not None:
                chunks.append(np.asarray(audio, dtype=np.float32))
        chunks.append(PAUSE)
    if not chunks:
        raise RuntimeError("Kokoro produced no audio")
    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "ep.wav"
        mp3 = Path(td) / "ep.mp3"
        sf.write(wav, np.concatenate(chunks), SR)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
                        "-ac", "1", "-b:a", "64k", str(mp3)], check=True)
        out_mp3.write_bytes(mp3.read_bytes())


def duration_mmss(mp3: Path) -> str:
    secs = float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(mp3)]).decode().strip())
    s = int(round(secs))
    return f"{s // 60:02d}:{s % 60:02d}"


def update_manifest(date: str, mp3: Path) -> bool:
    path = FEED_DIR / "episodes_manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data if isinstance(data, list) else data.get("episodes", [])
    hit = None
    for e in entries:
        if str(e.get("filename", "")).endswith(mp3.name) or e.get("date") == date:
            hit = e
    if hit is None:
        print(f"manifest: no entry for {date}; audio replaced but feed not touched")
        return False
    hit["size_bytes"] = mp3.stat().st_size
    hit["duration"] = duration_mmss(mp3)
    hit["voice"] = f"kokoro-{VOICE}"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"manifest: {date} -> {hit['size_bytes']} bytes, {hit['duration']}")
    return True


def main(paths):
    changed = False
    for p in paths:
        txt = Path(p)
        if txt.suffix != ".txt" or not txt.exists():
            continue
        date = txt.stem
        mp3 = FEED_DIR / "episodes" / f"{date}.mp3"
        if not mp3.exists():
            print(f"skip {date}: {mp3} not published yet")
            continue
        print(f"Rendering {txt} with Kokoro voice {VOICE}")
        render(txt.read_text(encoding="utf-8"), mp3)
        changed |= update_manifest(date, mp3)
    if changed:
        subprocess.run([sys.executable, "generate_feed.py", BASE_URL], cwd=FEED_DIR, check=True)
        print("feed.xml rebuilt")


if __name__ == "__main__":
    main(sys.argv[1:])
