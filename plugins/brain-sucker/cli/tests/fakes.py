"""Test adapters for the YouTube, ClipSource and Transcriber seams."""
import json
from pathlib import Path

from brainsuck.clipsource import NeedsLogin, clip_info_from_ytdlp, parse_clip_url
from brainsuck.models import Segment, VideoRef
from brainsuck.transcript import parse_json3
from brainsuck.youtube import Blocked, ChannelCandidate, Unavailable, info_from_ytdlp


class FixtureClipSource:
    """Serves tests/fixtures/clips/info/<clip key>.json. Sets name Clip Keys that misbehave:
    `needs_login` raise NeedsLogin unless called with a browser in `cookie_ok`; `unavailable` and `blocked` raise."""

    def __init__(self, root: Path, aliases: dict[str, str] | None = None, needs_login: set[str] = frozenset(),
                 cookie_ok: set[str] = frozenset(), unavailable: set[str] = frozenset(),
                 blocked: set[str] = frozenset()):
        self.root = root
        self.aliases = aliases or {}
        self.needs_login, self.cookie_ok = set(needs_login), set(cookie_ok)
        self.unavailable, self.blocked = set(unavailable), set(blocked)
        self.info_calls: list[tuple[str, str | None]] = []

    def _key(self, url: str) -> str:
        k = parse_clip_url(url)
        key = k.key if k else self.aliases.get(url)
        if key is None or not (self.root / "info" / f"{key}.json").exists():
            raise Unavailable("unsupported", url)
        return key

    def fetch_info(self, url, cookies=None):
        self.info_calls.append((url, cookies))
        key = self._key(url)
        if key in self.blocked:
            raise Blocked("HTTP Error 429")
        if key in self.unavailable:
            raise Unavailable("unavailable")
        if key in self.needs_login and cookies not in self.cookie_ok:
            raise NeedsLogin("login required")
        return clip_info_from_ytdlp(json.loads((self.root / "info" / f"{key}.json").read_text(encoding="utf-8")))

    def _fake_file(self, url, dest_dir, suffix):
        dest_dir.mkdir(parents=True, exist_ok=True)
        p = dest_dir / f"{self._key(url)}.{suffix}"
        p.write_bytes(b"fake")
        return p

    def fetch_audio(self, url, dest_dir, cookies=None):
        return self._fake_file(url, dest_dir, "audio.m4a")

    def fetch_video_360p(self, url, dest_dir, cookies=None):
        return self._fake_file(url, dest_dir, "v360.mp4")


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
    def __init__(self, text_by_file: dict[str, str] | None = None, detected: str = "en",
                 low_conf_files: set[str] = frozenset(), empty_files: set[str] = frozenset()):
        self.text_by_file = text_by_file or {}
        self.detected = detected
        self.low_conf_files = set(low_conf_files)
        self.empty_files = set(empty_files)
        self.calls = 0
        self.last_prompt: str | None = None
        self.last_lang: str | None = None

    def transcribe(self, audio: Path, lang: str) -> list[Segment]:
        self.calls += 1
        return [Segment(0.0, self.text_by_file.get(audio.name, f"ถอดเสียง {audio.stem} ({lang})"))]

    def transcribe_clip(self, audio: Path, lang: str | None, prompt: str) -> tuple[list[Segment], str]:
        """Two segments (0 s and 40 s → two transcript lines); the second is low-confidence for low_conf_files."""
        self.calls += 1
        self.last_prompt, self.last_lang = prompt, lang
        if audio.name in self.empty_files:
            return [], lang or self.detected
        return [Segment(0.0, f"ถอดเสียง {audio.stem}"),
                Segment(40.0, "ช่วงที่สอง", audio.name in self.low_conf_files)], lang or self.detected
