from dataclasses import dataclass, field
from datetime import date
from typing import Literal

Kind = Literal["long", "short"]
Platform = Literal["youtube", "instagram", "tiktok"]
TranscriptSource = Literal["youtube-manual", "youtube-auto", "whisper-large-v3", "nexlev-description"]


@dataclass(frozen=True)
class Segment:
    start: float
    text: str
    low_conf: bool = False


@dataclass(frozen=True)
class VideoRef:
    id: str
    title: str
    kind: Kind


@dataclass(frozen=True)
class VideoInfo:
    id: str
    channel_id: str
    title: str
    description: str
    published: date
    duration: int
    kind: Kind
    url: str
    lang: str
    captions: dict[str, Literal["manual", "auto"]]


@dataclass(frozen=True)
class VideoRecord:
    id: str
    channel_id: str
    title: str
    kind: Kind
    published: date
    duration: int
    url: str
    lang: str
    transcript_source: TranscriptSource
    status: Literal["active", "removed"]
    summary_status: Literal["pending", "done"]
    topics: list[str]
    screen_frames: list[str]
    summary_md: str
    description: str
    transcript_lines: list[str]
    screen_text_lines: list[str] = field(default_factory=list)
    platform: Platform | None = None
    display_name: str | None = None
    creator: str | None = None
    transcript_quality: float | None = None
    copied_to: list[str] = field(default_factory=list)
