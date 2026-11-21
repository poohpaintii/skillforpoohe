#!/usr/bin/env python3
"""Turn a Thai (or any language) teaching script into an MP3 file.

Usage:
    python make_audio.py script.txt out.mp3 [--voice th-TH-PremwadeeNeural]
                         [--rate +0%] [--engine auto|edge|gtts|espeak]
                         [--lang th]

Script format (plain UTF-8 text):
    - Paragraphs are separated by blank lines. Each paragraph becomes one
      TTS chunk, followed by a short natural pause.
    - A line containing only [pause] or [pause 3] inserts silence (seconds).
    - Lines starting with '#' are treated as comments/headings and are skipped,
      so the same file can carry section notes for a human reader.

Engines, tried in this order with --engine auto:
    1. edge-tts  (pip install edge-tts) - natural neural voices, needs internet.
       Thai voices: th-TH-PremwadeeNeural (female), th-TH-NiwatNeural (male).
    2. gTTS      (pip install gTTS)     - Google voice, needs internet.
    3. espeak-ng (apt install espeak-ng) - offline, robotic but always works.
ffmpeg is required to join the pieces.
"""
import argparse
import asyncio
import os
import re
import shutil
import subprocess
import sys
import tempfile

MAX_CHARS = 450  # keep each TTS request small; long requests fail or sound rushed
PARA_PAUSE = 0.7  # seconds of silence between paragraphs


def parse_script(text):
    """Return a list of ('speak', str) / ('pause', seconds) items."""
    items, buf = [], []

    def flush():
        if buf:
            para = " ".join(s.strip() for s in buf if s.strip())
            if para:
                for piece in split_long(para):
                    items.append(("speak", piece))
                items.append(("pause", PARA_PAUSE))
            buf.clear()

    for line in text.splitlines():
        s = line.strip()
        m = re.fullmatch(r"\[pause(?:\s+([\d.]+))?\]", s, re.I)
        if m:
            flush()
            items.append(("pause", float(m.group(1) or 1.5)))
        elif s.startswith("#"):
            flush()
        elif not s:
            flush()
        else:
            buf.append(s)
    flush()
    return items


def split_long(para):
    """Split at sentence ends / spaces (Thai uses spaces between phrases)."""
    if len(para) <= MAX_CHARS:
        return [para]
    parts, cur = [], ""
    for tok in re.split(r"(?<=[.!?。])\s+|\s+", para):
        if cur and len(cur) + 1 + len(tok) > MAX_CHARS:
            parts.append(cur)
            cur = tok
        else:
            cur = f"{cur} {tok}".strip()
    if cur:
        parts.append(cur)
    return parts


# ---------------------------------------------------------------- engines
def edge_engine(voice, rate):
    import edge_tts  # noqa: F401  (fail fast if missing)

    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

    def speak(text, path):
        async def run():
            kw = {"voice": voice, "rate": rate}
            if proxy:
                kw["proxy"] = proxy
            await edge_tts.Communicate(text, **kw).save(path)
        asyncio.run(run())
    return speak


def gtts_engine(lang):
    from gtts import gTTS

    def speak(text, path):
        gTTS(text, lang=lang).save(path)
    return speak


def espeak_engine(lang, rate):
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        raise RuntimeError("espeak-ng not installed")
    # map "+10%" style rate to words-per-minute around a slow teaching pace
    pct = int(re.sub(r"[^\d-]", "", rate) or 0)
    wpm = str(int(150 * (1 + pct / 100)))

    def speak(text, path):
        wav = path[:-4] + ".wav"
        subprocess.run([exe, "-v", lang, "-s", wpm, "-w", wav, text], check=True,
                       capture_output=True)
        to_mp3(wav, path)
    return speak


def to_mp3(src, dst):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src,
                    "-ar", "24000", "-ac", "1", "-b:a", "64k", dst], check=True)


def silence(path, seconds):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "anullsrc=r=24000:cl=mono", "-t", str(seconds),
                    "-b:a", "64k", path], check=True)


def pick_engine(name, args):
    order = ["edge", "gtts", "espeak"] if name == "auto" else [name]
    builders = {
        "edge": lambda: edge_engine(args.voice, args.rate),
        "gtts": lambda: gtts_engine(args.lang),
        "espeak": lambda: espeak_engine(args.lang, args.rate),
    }
    errors = []
    for eng in order:
        try:
            speak = builders[eng]()
            with tempfile.TemporaryDirectory() as d:  # probe with a tiny request
                probe = os.path.join(d, "probe.mp3")
                speak("ทดสอบ" if args.lang == "th" else "test", probe)
                if os.path.getsize(probe) == 0:
                    raise RuntimeError("empty audio")
            return eng, speak
        except Exception as e:  # try the next engine
            errors.append(f"{eng}: {type(e).__name__}: {str(e)[:120]}")
    sys.exit("No TTS engine worked:\n  " + "\n  ".join(errors))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script")
    ap.add_argument("output")
    ap.add_argument("--voice", default="th-TH-PremwadeeNeural")
    ap.add_argument("--rate", default="-5%", help="speed, e.g. -10%% slower, +10%% faster")
    ap.add_argument("--lang", default="th")
    ap.add_argument("--engine", default="auto", choices=["auto", "edge", "gtts", "espeak"])
    args = ap.parse_args()

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg is required (apt install ffmpeg / brew install ffmpeg)")

    with open(args.script, encoding="utf-8") as f:
        items = parse_script(f.read())
    if not items:
        sys.exit("script is empty")

    engine, speak = pick_engine(args.engine, args)
    print(f"engine: {engine}", file=sys.stderr)

    with tempfile.TemporaryDirectory() as d:
        files = []
        total = sum(1 for k, _ in items if k == "speak")
        n = 0
        for i, (kind, val) in enumerate(items):
            p = os.path.join(d, f"{i:05d}.mp3")
            if kind == "pause":
                silence(p, val)
            else:
                n += 1
                for attempt in range(3):
                    try:
                        speak(val, p)
                        break
                    except Exception:
                        if attempt == 2:
                            raise
                print(f"  [{n}/{total}] {val[:40]}...", file=sys.stderr)
            files.append(p)
        lst = os.path.join(d, "list.txt")
        with open(lst, "w") as f:
            f.writelines(f"file '{p}'\n" for p in files)
        # re-encode while joining so pieces from any engine fit together cleanly
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", lst, "-ar", "24000", "-ac", "1", "-b:a", "64k",
                        args.output], check=True)

    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", args.output], capture_output=True, text=True)
    secs = float(dur.stdout.strip() or 0)
    print(f"saved {args.output}  ({int(secs // 60)}:{int(secs % 60):02d} min, engine={engine})")


if __name__ == "__main__":
    main()
