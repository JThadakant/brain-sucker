"""Transcript source policy, YouTube json3 parsing and [mm:ss] line formatting."""
import re

from brainsuck.models import Segment, TranscriptSource

_NOISE = re.compile(r"\[(?:music|applause|laughter)\]|>>", re.IGNORECASE)
WHISPER: TranscriptSource = "whisper-large-v3"
UNCLEAR = " ⟨ถอดไม่ชัด⟩"
UNCLEAR_LOGPROB = -1.0


def detect_lang(info_json: dict) -> str:
    if info_json.get("language"):
        return info_json["language"]
    for key in info_json.get("automatic_captions") or {}:
        if key.endswith("-orig"):
            return key[: -len("-orig")]
    return "en"


def choose_source(lang: str, captions: dict[str, str]) -> tuple[TranscriptSource, str | None]:
    """Thai → Whisper always (YouTube's Thai auto captions are too noisy; see docs/research/0002)."""
    if lang == "th":
        return WHISPER, None
    if captions.get(lang) == "manual":
        return "youtube-manual", lang
    if f"{lang}-orig" in captions:
        return "youtube-auto", f"{lang}-orig"
    return WHISPER, None


def parse_json3(data: dict) -> list[Segment]:
    out = []
    for ev in data.get("events", []):
        text = "".join(s.get("utf8", "") for s in ev.get("segs") or [])
        text = " ".join(_NOISE.sub(" ", text).split())
        if text:
            out.append(Segment(ev.get("tStartMs", 0) / 1000, text))
    return out


def _stamp(seconds: float) -> str:
    s = int(seconds)
    h, m, sec = s // 3600, s % 3600 // 60, s % 60
    return f"[{h}:{m:02d}:{sec:02d}]" if h else f"[{m:02d}:{sec:02d}]"


def format_lines(segments: list[Segment], window: float = 30.0) -> list[str]:
    """[mm:ss] lines, one per `window` seconds; a line with any low-confidence segment ends with UNCLEAR."""
    lines: list[tuple[float, list[str], list[bool]]] = []
    for seg in segments:
        if not lines or seg.start - lines[-1][0] >= window:
            lines.append((seg.start, [], []))
        lines[-1][1].append(seg.text.strip())
        lines[-1][2].append(seg.low_conf)
    return [f"{_stamp(start)} {' '.join(texts)}{UNCLEAR if any(low) else ''}" for start, texts, low in lines]


def transcript_quality(lines: list[str]) -> float:
    """Share of transcript lines marked UNCLEAR."""
    if not lines:
        return 0.0
    return round(sum(l.endswith(UNCLEAR) for l in lines) / len(lines), 2)


_URL = re.compile(r"https?://\S+")
_HASHTAG = re.compile(r"#\S+")


def whisper_prompt(title: str, creator: str, description: str, limit: int = 300) -> str:
    """Whisper initial_prompt: names and terms the clip is likely to say, so Whisper spells them right."""
    desc = _HASHTAG.sub(" ", _URL.sub(" ", description))
    parts = [" ".join(p.split()) for p in (title, creator, desc)]
    return ". ".join(p for p in parts if p)[:limit]
