"""On-disk Channel Knowledge for one Channel: state.json, Video Records, index.md, skipped.md."""
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator

from brainsuck.models import VideoRecord
from brainsuck.record import parse_record, record_filename, render_record
from brainsuck.sync import KnownVideo


@dataclass(frozen=True)
class ChannelState:
    channel_id: str
    handle: str | None
    folder: str
    title: str
    known: dict[str, KnownVideo]
    skipped: dict[str, str]


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def _video_id(path: Path) -> str:
    return path.stem.split("_", 1)[1]


class ChannelStore:
    def __init__(self, channel_dir: Path):
        self.channel_dir = channel_dir
        self.videos_dir = channel_dir / "videos"

    def load_state(self) -> ChannelState | None:
        p = self.channel_dir / "state.json"
        if not p.exists():
            return None
        d = json.loads(p.read_text(encoding="utf-8"))
        d["known"] = {k: KnownVideo(**v) for k, v in d["known"].items()}
        return ChannelState(**d)

    def save_state(self, s: ChannelState) -> None:
        atomic_write(self.channel_dir / "state.json", json.dumps(asdict(s), ensure_ascii=False, indent=1))

    def _paths(self) -> Iterator[Path]:
        if self.videos_dir.exists():
            yield from sorted(self.videos_dir.glob("*.md"))

    def write_record(self, r: VideoRecord) -> Path:
        path = self.videos_dir / record_filename(r)
        for old in self._paths():
            if _video_id(old) == r.id and old != path:
                old.unlink()
        atomic_write(path, render_record(r))
        return path

    def read_record(self, video_id: str) -> VideoRecord | None:
        for p in self._paths():
            if _video_id(p) == video_id:
                return parse_record(p.read_text(encoding="utf-8"))
        return None

    def iter_records(self) -> Iterator[VideoRecord]:
        for p in self._paths():
            yield parse_record(p.read_text(encoding="utf-8"))

    def write_index(self) -> None:
        records = sorted(self.iter_records(), key=lambda r: r.published, reverse=True)
        lines = ["# Index", "", "| วันที่ | ประเภท | ชื่อ | สรุปแล้ว | ไฟล์ |", "|---|---|---|---|---|"]
        for r in records:
            title = r.title.replace("|", r"\|") + (" (ลบแล้ว)" if r.status == "removed" else "")
            done = "✓" if r.summary_status == "done" else ""
            lines.append(f"| {r.published.isoformat()} | {r.kind} | {title} | {done} | "
                         f"[{record_filename(r)}](videos/{record_filename(r)}) |")
        atomic_write(self.channel_dir / "index.md", "\n".join(lines) + "\n")

    def write_skipped(self) -> None:
        s = self.load_state()
        lines = ["# Skipped Videos", "", "| id | เหตุผล | ลิงก์ |", "|---|---|---|"]
        for vid, reason in (s.skipped if s else {}).items():
            lines.append(f"| {vid} | {reason} | https://www.youtube.com/watch?v={vid} |")
        atomic_write(self.channel_dir / "skipped.md", "\n".join(lines) + "\n")
