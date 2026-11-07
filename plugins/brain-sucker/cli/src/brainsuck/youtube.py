"""YouTube seam: everything Brain Sucker needs from YouTube, behind one Protocol. Production adapter = yt-dlp."""
import json
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal, Protocol

from brainsuck.models import Kind, Segment, VideoInfo, VideoRef
from brainsuck.transcript import detect_lang, parse_json3


@dataclass(frozen=True)
class ChannelCandidate:
    channel_id: str
    title: str
    handle: str | None
    subscribers: int | None
    video_count: int | None


class YouTubeError(Exception):
    """Something went wrong talking to YouTube that is neither a block nor a per-video restriction."""


class Blocked(YouTubeError):
    """YouTube is rate-limiting or bot-checking us. Stop the run; retry later."""


UnavailableReason = Literal["members-only", "age-restricted", "private", "live", "unavailable"]


class Unavailable(YouTubeError):
    def __init__(self, reason: UnavailableReason, detail: str = ""):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


class YouTube(Protocol):
    def resolve(self, query: str) -> list[ChannelCandidate]: ...
    def list_channel(self, channel_id: str) -> tuple[ChannelCandidate, list[VideoRef]]: ...
    def fetch_info(self, video_id: str) -> VideoInfo: ...
    def fetch_captions(self, video_id: str, key: str) -> list[Segment]: ...
    def fetch_audio(self, video_id: str, dest_dir: Path) -> Path: ...
    def fetch_video_360p(self, video_id: str, dest_dir: Path) -> Path: ...


_BLOCK_MARKERS = ("not a bot", "http error 429", "too many requests")
_UNAVAILABLE_MARKERS: list[tuple[str, UnavailableReason]] = [
    ("members-only", "members-only"), ("channel's members", "members-only"), ("join this channel", "members-only"),
    ("confirm your age", "age-restricted"), ("age-restricted", "age-restricted"),
    ("private video", "private"),
    ("live event", "live"), ("premieres in", "live"),
    ("video unavailable", "unavailable"), ("has been removed", "unavailable"), ("not available", "unavailable"),
    ("has been terminated", "unavailable"),
]
_LIVE = {"is_live", "is_upcoming", "was_live", "post_live"}


def classify_error(message: str) -> YouTubeError:
    m = message.lower()
    if any(k in m for k in _BLOCK_MARKERS):
        return Blocked(message)
    for marker, reason in _UNAVAILABLE_MARKERS:
        if marker in m:
            return Unavailable(reason, message)
    return YouTubeError(message)


def _published(d: dict) -> date:
    if d.get("upload_date"):
        return datetime.strptime(d["upload_date"], "%Y%m%d").date()
    if d.get("timestamp"):
        return datetime.fromtimestamp(d["timestamp"], tz=timezone.utc).date()
    return date.today()


def info_from_ytdlp(d: dict, kind_hint: Kind | None) -> VideoInfo:
    """Map a yt-dlp info dict to VideoInfo, raising Unavailable for videos Brain Sucker never ingests."""
    availability = d.get("availability")
    if availability in ("subscriber_only", "premium_only"):
        raise Unavailable("members-only")
    if availability == "needs_auth":
        raise Unavailable("age-restricted" if (d.get("age_limit") or 0) >= 18 else "private")
    if availability == "private":
        raise Unavailable("private")
    if d.get("live_status") in _LIVE:
        raise Unavailable("live")
    lang = detect_lang(d)
    captions: dict[str, Literal["manual", "auto"]] = {
        k: "auto" for k in d.get("automatic_captions") or {} if k in (lang, f"{lang}-orig")}
    captions.update({k: "manual" for k in d.get("subtitles") or {} if k != "live_chat"})
    vertical = (d.get("height") or 0) > (d.get("width") or 0)
    kind = kind_hint or ("short" if vertical and (d.get("duration") or 0) <= 180 else "long")
    return VideoInfo(
        id=d["id"], channel_id=d.get("channel_id") or "", title=d.get("title") or "",
        description=d.get("description") or "", published=_published(d), duration=int(d.get("duration") or 0),
        kind=kind, url=d.get("webpage_url") or f"https://www.youtube.com/watch?v={d['id']}", lang=lang,
        captions=captions,
    )


def _candidate(d: dict, video_count: int | None = None) -> ChannelCandidate:
    uploader_id = str(d.get("uploader_id") or "")
    return ChannelCandidate(
        channel_id=d.get("channel_id") or d.get("id"),
        title=d.get("channel") or d.get("uploader") or d.get("title"),
        handle=uploader_id if uploader_id.startswith("@") else None,
        subscribers=d.get("channel_follower_count"),
        video_count=video_count,
    )


class YtDlpYouTube:
    """Talks to YouTube through yt-dlp's Python API. Node is the JS runtime; never uses cookies."""

    def __init__(self, sleep_requests: float = 0.75, sleep_captions: float = 3.0, sleep_download: float = 5.0):
        self.sleep_requests = sleep_requests
        self.sleep_captions = sleep_captions
        self.sleep_download = sleep_download
        self._kinds: dict[str, Kind] = {}
        self._raw: dict[str, dict] = {}

    def _ydl(self, **extra):
        import yt_dlp

        opts = {"quiet": True, "no_warnings": True, "noprogress": True, "js_runtimes": {"node": {}},
                "sleep_interval_requests": self.sleep_requests}
        opts.update(extra)
        return yt_dlp.YoutubeDL(opts)

    def _run(self, url: str, download: bool = False, **extra) -> tuple[dict, str | None]:
        import yt_dlp

        try:
            with self._ydl(**extra) as y:
                d = y.extract_info(url, download=download)
                return d, (y.prepare_filename(d) if download else None)
        except yt_dlp.utils.DownloadError as e:
            raise classify_error(str(e)) from e

    def resolve(self, query: str) -> list[ChannelCandidate]:
        q = query.strip()
        if q.startswith("http"):
            url = q.rstrip("/")
        elif q.startswith("@"):
            url = f"https://www.youtube.com/{q}"
        elif q.startswith("UC") and len(q) == 24:
            url = f"https://www.youtube.com/channel/{q}"
        else:
            return self._search(q)
        d, _ = self._run(url + "/videos", extract_flat="in_playlist", playlistend=1)
        return [_candidate(d)]

    def _search(self, text: str) -> list[ChannelCandidate]:
        d, _ = self._run(f"ytsearch10:{text}", extract_flat="in_playlist")
        ids: list[str] = []
        for e in d.get("entries") or []:
            if e.get("channel_id") and e["channel_id"] not in ids:
                ids.append(e["channel_id"])
        return [self.resolve(cid)[0] for cid in ids[:3]]

    def list_channel(self, channel_id: str) -> tuple[ChannelCandidate, list[VideoRef]]:
        refs: list[VideoRef] = []
        meta = None
        for tab, kind in (("videos", "long"), ("shorts", "short")):
            try:
                d, _ = self._run(f"https://www.youtube.com/channel/{channel_id}/{tab}", extract_flat="in_playlist",
                                 extractor_args={"youtubetab": {"approximate_date": [""]}})
            except YouTubeError as e:
                if isinstance(e, Blocked) or "does not have" not in str(e).lower():
                    raise
                continue
            meta = meta or d
            for e in d.get("entries") or []:
                if e.get("live_status") in ("is_live", "is_upcoming"):
                    continue
                self._kinds[e["id"]] = kind
                refs.append(VideoRef(e["id"], e.get("title") or "", kind))
        if meta is None:
            raise YouTubeError(f"channel {channel_id} has no videos or shorts tab")
        return _candidate(meta, video_count=len(refs)), refs

    def fetch_info(self, video_id: str) -> VideoInfo:
        d, _ = self._run(f"https://www.youtube.com/watch?v={video_id}")
        self._raw[video_id] = d
        return info_from_ytdlp(d, self._kinds.get(video_id))

    def fetch_captions(self, video_id: str, key: str) -> list[Segment]:
        d = self._raw.get(video_id) or self._run(f"https://www.youtube.com/watch?v={video_id}")[0]
        tracks = (d.get("subtitles") or {}).get(key) or (d.get("automatic_captions") or {}).get(key) or []
        track = next((t for t in tracks if t.get("ext") == "json3"), None)
        if track is None:
            raise YouTubeError(f"no json3 captions '{key}' for {video_id}")
        time.sleep(self.sleep_captions)
        try:
            with self._ydl() as y:
                data = json.loads(y.urlopen(track["url"]).read().decode("utf-8"))
        except Exception as e:  # yt-dlp raises its own HTTPError types; 429 must become Blocked
            raise classify_error(str(e)) from e
        return parse_json3(data)

    def _download(self, video_id: str, dest_dir: Path, suffix: str, **fmt) -> Path:
        dest_dir.mkdir(parents=True, exist_ok=True)
        _, path = self._run(f"https://www.youtube.com/watch?v={video_id}", download=True,
                            outtmpl=str(dest_dir / f"%(id)s.{suffix}.%(ext)s"), sleep_interval=self.sleep_download,
                            **fmt)
        return Path(path)

    def fetch_audio(self, video_id: str, dest_dir: Path) -> Path:
        return self._download(video_id, dest_dir, "audio", format="ba[ext=m4a]/ba")

    def fetch_video_360p(self, video_id: str, dest_dir: Path) -> Path:
        return self._download(video_id, dest_dir, "v360", format="bv*[height<=360]/b[height<=360]/wv*",
                              format_sort=["res:360", "+size"])
