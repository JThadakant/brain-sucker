"""Video Record <-> markdown. Format: docs/DESIGN.md § รูปแบบ Video Record."""
import re
from dataclasses import replace
from datetime import date

import yaml

from brainsuck.models import VideoInfo, VideoRecord

_FRONT = ["id", "channel_id", "title", "kind", "published", "duration", "url", "lang",
          "transcript_source", "status", "summary_status", "topics", "screen_frames"]
_FRONT_KEY = {"summary_status": "summary"}


def record_filename(r: VideoRecord) -> str:
    return f"{r.published:%Y-%m-%d}_{r.id}.md"


_HEADINGISH = re.compile(r"^\\*#")
_ESCAPED = re.compile(r"^\\+#")


def _escape(text: str) -> str:
    """Prefix one backslash to lines that would read as headings, so user text can't open a section."""
    return "\n".join("\\" + l if _HEADINGISH.match(l) else l for l in text.splitlines())


def _unescape(text: str) -> str:
    return "\n".join(l[1:] if _ESCAPED.match(l) else l for l in text.splitlines())


def render_record(r: VideoRecord) -> str:
    front = {_FRONT_KEY.get(k, k): getattr(r, k) for k in _FRONT}
    front["published"] = r.published.isoformat()
    parts = [
        "---\n" + yaml.safe_dump(front, allow_unicode=True, sort_keys=False) + "---",
        "## Summary\n" + r.summary_md.strip(),
        "## Description\n" + _escape(r.description.strip()),
        "## Transcript\n" + "\n".join(r.transcript_lines),
    ]
    if r.screen_text_lines:
        parts.append("## Screen Text\n" + "\n".join(r.screen_text_lines))
    return "\n\n".join(parts) + "\n"


def _sections(body: str) -> dict[str, str]:
    out: dict[str, list[str]] = {}
    current = None
    for line in body.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            out[current] = []
        elif current is not None:
            out[current].append(line)
    return {k: "\n".join(v).strip("\n") for k, v in out.items()}


def parse_record(text: str) -> VideoRecord:
    _, front_text, body = text.split("---\n", 2)
    front = yaml.safe_load(front_text)
    sec = _sections(body)
    fields = {k: front[_FRONT_KEY.get(k, k)] for k in _FRONT}
    fields["published"] = date.fromisoformat(str(fields["published"]))
    fields["topics"] = list(fields["topics"] or [])
    fields["screen_frames"] = list(fields["screen_frames"] or [])
    return VideoRecord(
        **fields,
        summary_md=sec.get("Summary", "").strip(),
        description=_unescape(sec.get("Description", "").strip()),
        transcript_lines=[l for l in sec.get("Transcript", "").splitlines() if l.strip()],
        screen_text_lines=[l for l in sec.get("Screen Text", "").splitlines() if l.strip()],
    )


def refresh_metadata(r: VideoRecord, info: VideoInfo) -> VideoRecord:
    return replace(r, title=info.title, description=info.description, duration=info.duration)


def mark_removed(r: VideoRecord) -> VideoRecord:
    return replace(r, status="removed")
