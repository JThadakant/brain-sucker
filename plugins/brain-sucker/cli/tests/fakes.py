"""Test adapters for the YouTube and Transcriber seams."""
import json
from pathlib import Path

from brainsuck.models import Segment, VideoRef
from brainsuck.transcript import parse_json3
from brainsuck.youtube import Blocked, ChannelCandidate, info_from_ytdlp


class FixtureYouTube:
    """Serves tests/fixtures/youtube. `blocked_after=n` makes fetch_info call n+1 raise Blocked."""

    def __init__(self, root: Path, blocked_after: int | None = None, drop: set[str] = frozenset(),
                 titles: dict[str, str] | None = None):
        self.root = root
        self.blocked_after = blocked_after
        self.drop = set(drop)
        self.titles = titles or {}
        self.info_calls = 0
        self._channel = json.loads((root / "channel.json").read_text(encoding="utf-8"))
        self._kinds = {}

    def resolve(self, query):
        c = self._channel["channel"]
        hit = query.lower() in (c["title"].lower(), (c["handle"] or "").lower(), c["channel_id"].lower())
        return [ChannelCandidate(**c)] if hit else []

    def list_channel(self, channel_id):
        refs = []
        for kind in ("long", "short"):
            for e in self._channel[kind]:
                if e["id"] in self.drop:
                    continue
                self._kinds[e["id"]] = kind
                refs.append(VideoRef(e["id"], self.titles.get(e["id"], e["title"]), kind))
        return ChannelCandidate(**self._channel["channel"]), refs

    def fetch_info(self, video_id):
        self.info_calls += 1
        if self.blocked_after is not None and self.info_calls > self.blocked_after:
            raise Blocked("HTTP Error 429")
        d = json.loads((self.root / "info" / f"{video_id}.json").read_text(encoding="utf-8"))
        if video_id in self.titles:
            d["title"] = self.titles[video_id]
        return info_from_ytdlp(d, self._kinds.get(video_id))

    def fetch_captions(self, video_id, key):
        path = self.root / "captions" / f"{video_id}.{key}.json3"
        return parse_json3(json.loads(path.read_text(encoding="utf-8")))

    def _fake_file(self, video_id, dest_dir, suffix):
        dest_dir.mkdir(parents=True, exist_ok=True)
        p = dest_dir / f"{video_id}.{suffix}"
        p.write_bytes(b"fake")
        return p

    def fetch_audio(self, video_id, dest_dir):
        return self._fake_file(video_id, dest_dir, "audio.m4a")

    def fetch_video_360p(self, video_id, dest_dir):
        return self._fake_file(video_id, dest_dir, "v360.mp4")


class FakeTranscriber:
    def __init__(self, text_by_file: dict[str, str] | None = None):
        self.text_by_file = text_by_file or {}
        self.calls = 0

    def transcribe(self, audio: Path, lang: str) -> list[Segment]:
        self.calls += 1
        return [Segment(0.0, self.text_by_file.get(audio.name, f"ถอดเสียง {audio.stem} ({lang})"))]
