"""Scene-change keyframes for Screen Text (opt-in via --screen-text)."""
import os
import re
import shutil
import subprocess
from pathlib import Path


def find_ffmpeg() -> Path:
    found = shutil.which("ffmpeg")
    if found:
        return Path(found)
    packages = Path(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages")
    for exe in sorted(packages.glob("Gyan.FFmpeg_*/ffmpeg-*/bin/ffmpeg.exe")):
        return exe
    raise FileNotFoundError("ffmpeg not found: install with `winget install Gyan.FFmpeg`")


def _spread(items: list, n: int) -> list:
    if len(items) <= n:
        return items
    step = (len(items) - 1) / (n - 1) if n > 1 else 0
    return [items[round(i * step)] for i in range(n)]


def extract_scene_frames(video: Path, out_dir: Path, threshold: float = 0.4,
                         max_frames: int = 40) -> list[tuple[float, Path]]:
    """Frames at major scene changes, as (seconds, jpg). Keeps at most `max_frames`, evenly spread."""
    out_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [str(find_ffmpeg()), "-hide_banner", "-i", str(video), "-vf", f"select='gt(scene,{threshold})',showinfo",
         "-fps_mode", "vfr", "-q:v", "4", str(out_dir / "f%05d.jpg")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg scene detection failed: {proc.stderr[-500:]}")
    times = [float(t) for t in re.findall(r"pts_time:([\d.]+)", proc.stderr)]
    frames = list(zip(times, sorted(out_dir.glob("f*.jpg"))))
    kept = _spread(frames, max_frames)
    keep_paths = {p for _, p in kept}
    for _, p in frames:
        if p not in keep_paths:
            p.unlink()
    return kept
