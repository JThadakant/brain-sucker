"""Clip Library: one flat folder of Clip Video Records (clips/), index.md and config.json, usable from any folder."""
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator, Literal

from brainsuck.models import VideoRecord
from brainsuck.record import parse_record, render_record
from brainsuck.store import atomic_write

DEFAULT_LIBRARY = Path.home() / "OneDrive" / "Desktop" / "mini-brain"
_FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def clip_key_of(r: VideoRecord) -> str:
    return f"{r.platform}_{r.id}"


def slugify(name: str, max_len: int = 60) -> str:
    """A Display Name as a Windows-safe filename part; keeps Thai and emoji."""
    s = re.sub(r"-+", "-", re.sub(r"\s+", "-", _FORBIDDEN.sub(" ", name)).strip("-. "))
    return s[:max_len].strip("-. ")


def clip_filename(r: VideoRecord) -> str:
    slug = slugify(r.display_name) if r.display_name else ""
    return clip_key_of(r) + (f"__{slug}" if slug else "") + ".md"


@dataclass(frozen=True)
class LibraryConfig:
    ig_cookies: Literal["ask", "always"] = "ask"
    browser: str | None = None


def _named_like(path: Path, key: str) -> bool:
    return path.stem == key or path.stem.startswith(key + "__")


class ClipLibrary:
    def __init__(self, root: Path):
        self.root = root
        self.clips_dir = root / "clips"

    def load_config(self) -> LibraryConfig:
        p = self.root / "config.json"
        return LibraryConfig(**json.loads(p.read_text(encoding="utf-8"))) if p.exists() else LibraryConfig()

    def save_config(self, c: LibraryConfig) -> None:
        atomic_write(self.root / "config.json", json.dumps(asdict(c), ensure_ascii=False, indent=1))

    def iter_records(self) -> Iterator[tuple[Path, VideoRecord]]:
        if self.clips_dir.exists():
            for p in sorted(self.clips_dir.glob("*.md")):
                yield p, parse_record(p.read_text(encoding="utf-8"))

    def path_of(self, key: str) -> Path | None:
        if not self.clips_dir.exists():
            return None
        for p in sorted(self.clips_dir.glob("*.md")):
            if _named_like(p, key) and clip_key_of(parse_record(p.read_text(encoding="utf-8"))) == key:
                return p
        return None

    def read(self, key: str) -> VideoRecord | None:
        p = self.path_of(key)
        return parse_record(p.read_text(encoding="utf-8")) if p else None

    def write(self, r: VideoRecord) -> Path:
        """Writes the record under its current name, drops stale names, refreshes Advisor copies and index.md."""
        key, name, text = clip_key_of(r), clip_filename(r), render_record(r)
        old = self.path_of(key)
        path = self.clips_dir / name
        atomic_write(path, text)
        if old and old != path:
            old.unlink()
        if r.summary_status == "done" and r.display_name:
            for advisor in map(Path, r.copied_to):
                if advisor.is_dir():
                    _write_copy(advisor / "clips", key, name, text)
        self.write_index()
        return path

    def write_index(self) -> None:
        rows = sorted((r for _, r in self.iter_records()), key=lambda r: r.published, reverse=True)
        lines = ["# Clip Library", "", "| ชื่อ | แพลตฟอร์ม | ผู้สร้าง | วันที่ | แท็ก | ไฟล์ |", "|---|---|---|---|---|---|"]
        for r in rows:
            name = r.display_name or r.title + (" (รอสรุป)" if r.summary_status == "pending" else "")
            cells = [name, r.platform or "", r.creator or "", r.published.isoformat(), ", ".join(r.topics)]
            f = clip_filename(r)
            lines.append("| " + " | ".join(c.replace("|", r"\|") for c in cells) + f" | [{f}](clips/{f}) |")
        atomic_write(self.root / "index.md", "\n".join(lines) + "\n")


def _write_copy(clips_dir: Path, key: str, name: str, text: str) -> None:
    if clips_dir.exists():
        for p in clips_dir.glob("*.md"):
            if p.name != name and _named_like(p, key):
                if clip_key_of(parse_record(p.read_text(encoding="utf-8"))) == key:
                    p.unlink()
    atomic_write(clips_dir / name, text)


def _stale(path: Path, r: VideoRecord) -> bool:
    """A done, named Clip whose Advisor copy is missing or differs (e.g. re-summarized in place after --refresh)."""
    if r.summary_status != "done" or not r.display_name:
        return False
    text = path.read_text(encoding="utf-8")
    for advisor in map(Path, r.copied_to):
        copy = advisor / "clips" / path.name
        if advisor.is_dir() and (not copy.exists() or copy.read_text(encoding="utf-8") != text):
            return True
    return False


def library_status(lib: ClipLibrary) -> dict:
    records = list(lib.iter_records())
    return {
        "stale_copies": [clip_key_of(r) for p, r in records if _stale(p, r)],
        "library": str(lib.root.resolve()),
        "config": asdict(lib.load_config()),
        "clips": len(records),
        "pending": [str(p.resolve()) for p, r in records if r.summary_status == "pending"],
        "unnamed": [clip_key_of(r) for _, r in records if r.summary_status == "done" and not r.display_name],
    }
