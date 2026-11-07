"""PROTOTYPE — throwaway. Phase 1 spike for Brain Sucker. Do not import from real code."""
import os
import pathlib
import subprocess
import sys
import time

CACHE = pathlib.Path(r"C:\brain-sucker-cache\proto")
OUT = CACHE / "out"
OUT.mkdir(parents=True, exist_ok=True)

FFMPEG_BIN = next(
    pathlib.Path(os.environ["LOCALAPPDATA"], "Microsoft", "WinGet", "Packages").glob(
        "Gyan.FFmpeg_*/ffmpeg-*/bin"
    )
)
os.environ["PATH"] = str(FFMPEG_BIN) + os.pathsep + os.environ["PATH"]

# test set: (video id, label, language)
CLIPS = [
    ("K_SXQoMdSf4", "nick-long-beef-stew-6m", "en"),
    ("cM5IAypOOfM", "nick-long-chocolate-33m", "en"),
    ("wrZZf2ER3ak", "nick-short-chives", "en"),
    ("LexQiGdPlxU", "thai-makro-2m", "th"),
]

YTDLP = [str(CACHE / "venv-asr" / "Scripts" / "python.exe"), "-m", "yt_dlp", "--js-runtimes", "node", "--no-progress"]


def run(cmd, **kw):
    t = time.perf_counter()
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)
    return p, time.perf_counter() - t


def url(vid):
    return f"https://www.youtube.com/watch?v={vid}"
