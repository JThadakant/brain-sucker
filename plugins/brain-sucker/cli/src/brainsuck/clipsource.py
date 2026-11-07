"""ClipSource seam: one Clip from a YouTube / TikTok / Instagram URL. Production adapter = yt-dlp.

Unlike the YouTube seam, Instagram may use the user's browser cookies — only when asked, only for Instagram."""
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol
from urllib.parse import parse_qs, urlparse

from brainsuck.frames import find_ffmpeg
from brainsuck.models import Kind, Platform
from brainsuck.youtube import Unavailable, YouTubeError, _published, classify_error, info_from_ytdlp


@dataclass(frozen=True)
class ClipKey:
    platform: Platform
    id: str

    @property
    def key(self) -> str:
        return f"{self.platform}_{self.id}"


@dataclass(frozen=True)
class ClipInfo:
    key: ClipKey
    url: str
    title: str
    description: str
    creator: str
    published: date
    duration: int
    kind: Kind
    lang: str | None


class NeedsLogin(YouTubeError):
    """Instagram wants a logged-in session for this Clip."""


_YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YT_PATH = re.compile(r"^/(?:shorts|live|embed)/([A-Za-z0-9_-]{11})")
_TIKTOK = re.compile(r"^/@[^/]+/video/(\d+)")
_INSTAGRAM = re.compile(r"^/(?:[^/]+/)?(?:reels?|p|tv)/([A-Za-z0-9_-]+)")


def parse_clip_url(url: str) -> ClipKey | None:
    """The Clip Key a URL names, without touching the network. None when only the site can tell (short links)."""
    u = urlparse(url.strip())
    host = (u.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    if host == "youtu.be":
        vid = u.path.strip("/").split("/")[0]
        return ClipKey("youtube", vid) if _YT_ID.match(vid) else None
    if host in ("youtube.com", "music.youtube.com"):
        vid = (parse_qs(u.query).get("v") or [""])[0] if u.path == "/watch" else ""
        m = _YT_PATH.match(u.path)
        vid = m.group(1) if m else vid
        return ClipKey("youtube", vid) if _YT_ID.match(vid) else None
    if host == "tiktok.com":
        m = _TIKTOK.match(u.path)
        return ClipKey("tiktok", m.group(1)) if m else None
    if host == "instagram.com":
        m = _INSTAGRAM.match(u.path)
        return ClipKey("instagram", m.group(1)) if m else None
    return None


_PLATFORMS: dict[str, Platform] = {"Youtube": "youtube", "TikTok": "tiktok", "Instagram": "instagram"}


def _youtube_lang(d: dict) -> str | None:
    """Base language code ("en-US" → "en"): Whisper rejects regional codes."""
    lang = d.get("language")
    if not lang:
        lang = next((k[: -len("-orig")] for k in d.get("automatic_captions") or {} if k.endswith("-orig")), None)
    return lang.split("-")[0].lower() if lang else None


def clip_info_from_ytdlp(d: dict) -> ClipInfo:
    platform = _PLATFORMS.get(d.get("extractor_key") or "")
    if platform is None:
        raise Unavailable("unsupported", d.get("extractor_key") or "")
    description = d.get("description") or ""
    title = d.get("title") or ""
    if platform == "youtube":
        yt = info_from_ytdlp(d, None)
        kind, lang = yt.kind, _youtube_lang(d)
    else:
        kind, lang = "short", None
    if platform == "instagram" and title.startswith("Video by "):
        first = next((l.strip() for l in description.splitlines() if l.strip()), "")
        title = first[:100] or title
    return ClipInfo(
        key=ClipKey(platform, d["id"]), url=d.get("webpage_url") or "", title=title, description=description,
        creator=d.get("uploader") or d.get("channel") or d.get("uploader_id") or "", published=_published(d),
        duration=int(d.get("duration") or 0), kind=kind, lang=lang,
    )


_LOGIN_MARKERS = ("login required", "log in", "cookies", "empty media response")


def classify_clip_error(message: str, platform: Platform | None) -> YouTubeError:
    if platform == "instagram" and any(k in message.lower() for k in _LOGIN_MARKERS):
        return NeedsLogin(message)
    return classify_error(message)


class ClipSource(Protocol):
    def fetch_info(self, url: str, cookies: str | None = None) -> ClipInfo: ...
    def fetch_audio(self, url: str, dest_dir: Path, cookies: str | None = None) -> Path: ...
    def fetch_video_360p(self, url: str, dest_dir: Path, cookies: str | None = None) -> Path: ...


class YtDlpClipSource:
    """`cookies` names a browser whose cookies yt-dlp reads; callers pass it for Instagram only."""

    def _opts(self, cookies: str | None, **extra) -> dict:
        """noplaylist: a pasted `watch?v=X&list=PL…` URL means video X, never the whole playlist."""
        opts = {"quiet": True, "no_warnings": True, "noprogress": True, "noplaylist": True,
                "js_runtimes": {"node": {}}, "ffmpeg_location": str(find_ffmpeg().parent)}
        if cookies:
            opts["cookiesfrombrowser"] = (cookies,)
        opts.update(extra)
        return opts

    def _run(self, url: str, cookies: str | None, download: bool = False, **extra) -> tuple[dict, str | None]:
        import yt_dlp

        key = parse_clip_url(url)
        try:
            with yt_dlp.YoutubeDL(self._opts(cookies, **extra)) as y:
                d = y.extract_info(url, download=download)
                return d, (y.prepare_filename(d) if download else None)
        except yt_dlp.utils.DownloadError as e:
            raise classify_clip_error(str(e), key.platform if key else None) from e
        except Exception as e:  # unreadable browser cookie store (locked DB, DPAPI) must not crash the batch
            if not cookies:
                raise
            raise YouTubeError(f"cookies from {cookies}: {e}") from e

    def fetch_info(self, url: str, cookies: str | None = None) -> ClipInfo:
        return clip_info_from_ytdlp(self._run(url, cookies)[0])

    def _download(self, url: str, dest_dir: Path, suffix: str, cookies: str | None, **fmt) -> Path:
        dest_dir.mkdir(parents=True, exist_ok=True)
        _, path = self._run(url, cookies, download=True, outtmpl=str(dest_dir / f"%(id)s.{suffix}.%(ext)s"), **fmt)
        return Path(path)

    def fetch_audio(self, url: str, dest_dir: Path, cookies: str | None = None) -> Path:
        return self._download(url, dest_dir, "audio", cookies, format="ba[ext=m4a]/ba/b")

    def fetch_video_360p(self, url: str, dest_dir: Path, cookies: str | None = None) -> Path:
        return self._download(url, dest_dir, "v360", cookies, format="bv*[height<=360]/b[height<=360]/wv*/b",
                              format_sort=["res:360", "+size"])
