from dataclasses import dataclass, field
from datetime import date
from typing import Literal

Kind = Literal["long", "short"]
TranscriptSource = Literal["youtube-manual", "youtube-auto", "whisper-large-v3"]


@dataclass(frozen=True)
class Segment:
    start: float
    text: str


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
