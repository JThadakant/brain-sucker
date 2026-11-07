"""Clip: turn pasted video URLs into Clip Video Records in the Clip Library. Dedups by Clip Key; one bad URL never
stops the batch, only a YouTube block does."""
import re
import shutil
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Callable

from brainsuck.clipsource import ClipInfo, ClipKey, ClipSource, NeedsLogin, parse_clip_url
from brainsuck.frames import extract_scene_frames
from brainsuck.library import ClipLibrary, LibraryConfig
from brainsuck.models import VideoRecord
from brainsuck.transcribe import Transcriber
from brainsuck.transcript import WHISPER, format_lines, transcript_quality, whisper_prompt
from brainsuck.youtube import Blocked, Unavailable, YouTubeError

BROWSERS = ("edge", "firefox", "chrome")


@dataclass(frozen=True)
class ClipResult:
    new: int
    existing: int
    refreshed: int
    skipped: int
    needs_login: int
    blocked: bool


class _NoSpeech(Exception):
    pass


class _LoginFailed(Exception):
    def __init__(self, tried: list[str]):
        super().__init__(tried)
        self.tried = tried


def _dedupe(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    out = []
    for u in urls:
        k = parse_clip_url(u)
        ident = k.key if k else u.strip()
        if ident not in seen:
            seen.add(ident)
            out.append(u)
    return out


def _browsers(ig_cookies: str | None, config: LibraryConfig) -> list[str]:
    if ig_cookies == "auto":
        return list(BROWSERS)
    if ig_cookies:
        return [ig_cookies]
    if config.ig_cookies == "always" and config.browser:
        return [config.browser]
    return []


def _merge(old: list[str], new: list[str]) -> list[str]:
    return old + [p for p in new if p not in old]


def _attach(library: ClipLibrary, old: VideoRecord, targets: list[str]) -> Path:
    """An already-stored Clip: rewrite it only when --to adds an Advisor, so hand edits to the file survive."""
    merged = _merge(old.copied_to, targets)
    if merged == old.copied_to:
        return library.path_of(f"{old.platform}_{old.id}")
    return library.write(replace(old, copied_to=merged))


def _fetch_info(source: ClipSource, url: str, key: ClipKey | None, browsers: list[str]) -> tuple[ClipInfo, str | None]:
    """Without cookies first; Instagram that needs a login then tries each browser's cookies in order."""
    try:
        return source.fetch_info(url), None
    except NeedsLogin:
        if not (key and key.platform == "instagram"):
            raise
    for b in browsers:
        try:
            return source.fetch_info(url, cookies=b), b
        except Blocked:
            raise
        except YouTubeError:
            continue
    raise _LoginFailed(browsers)


def _timed_frames(video: Path, out_dir: Path) -> list[str]:
    """Scene frames renamed t<seconds>.jpg, so the summarizer reads each frame's time from its name."""
    shutil.rmtree(out_dir, ignore_errors=True)
    kept: list[str] = []
    for sec, p in extract_scene_frames(video, out_dir, threshold=0.3, max_frames=40):
        target = out_dir / f"t{int(sec):05d}.jpg"
        if str(target) in kept:
            p.unlink()
            continue
        p.replace(target)
        kept.append(str(target))
    return kept


def _build(info: ClipInfo, url: str, cookies: str | None, source: ClipSource, transcriber: list[Transcriber],
           make_transcriber: Callable[[], Transcriber], cache_dir: Path, work: Path, visual: bool) -> VideoRecord:
    audio = source.fetch_audio(url, work, cookies)
    if not transcriber:
        transcriber.append(make_transcriber())
    segments, lang = transcriber[0].transcribe_clip(audio, info.lang,
                                                    whisper_prompt(info.title, info.creator, info.description))
    if not segments:
        raise _NoSpeech()
    frames: list[str] = []
    if visual:
        frames = _timed_frames(source.fetch_video_360p(url, work, cookies), cache_dir / "frames" / info.key.key)
    lines = format_lines(segments)
    return VideoRecord(
        id=info.key.id, channel_id="", title=info.title, kind=info.kind, published=info.published,
        duration=info.duration or int(segments[-1].start), url=info.url or url, lang=lang, transcript_source=WHISPER,
        status="active", summary_status="pending", topics=[], screen_frames=frames, summary_md="(pending)",
        description=info.description, transcript_lines=lines, platform=info.key.platform, creator=info.creator,
        transcript_quality=transcript_quality(lines),
    )


def clip(urls: list[str], library: ClipLibrary, *, source: ClipSource, make_transcriber: Callable[[], Transcriber],
         cache_dir: Path, visual: bool = True, refresh: bool = False, ig_cookies: str | None = None,
         remember: bool = False, to: list[Path] = (), emit: Callable[[dict], None] = lambda e: None) -> ClipResult:
    todo = _dedupe(urls)
    targets = [str(Path(p).resolve()) for p in to]
    config = library.load_config()
    counts = dict(new=0, existing=0, refreshed=0, skipped=0, needs_login=0)
    transcriber: list[Transcriber] = []
    blocked = False
    emit({"event": "start", "total": len(todo)})

    def done(status: str, i: int, path: Path, key: str, cookies: str | None = None) -> None:
        counts[status] += 1
        emit({"event": "clip", "key": key, "path": str(path), "status": status, "i": i, "n": len(todo),
              "cookies": cookies})

    for i, url in enumerate(todo, 1):
        key = parse_clip_url(url)
        try:
            old = library.read(key.key) if key else None
            if old and not refresh:
                done("existing", i, _attach(library, old, targets), key.key)
                continue
            info, cookies = _fetch_info(source, url, key, _browsers(ig_cookies, config))
            old = old or library.read(info.key.key)
            if old and not refresh:
                done("existing", i, _attach(library, old, targets), info.key.key)
                continue
            work = cache_dir / "work" / info.key.key
            try:
                rec = _build(info, url, cookies, source, transcriber, make_transcriber, cache_dir, work, visual)
            finally:
                shutil.rmtree(work, ignore_errors=True)
            if old:
                rec = replace(rec, display_name=old.display_name, copied_to=_merge(old.copied_to, targets))
            else:
                rec = replace(rec, copied_to=targets)
            if cookies and remember:
                config = LibraryConfig("always", cookies)
                library.save_config(config)
            done("refreshed" if old else "new", i, library.write(rec), info.key.key, cookies)
        except _LoginFailed as e:
            counts["needs_login"] += 1
            emit({"event": "needs-login", "url": url, "key": key.key if key else None, "tried": e.tried})
        except _NoSpeech:
            counts["skipped"] += 1
            emit({"event": "skipped", "url": url, "reason": "no-speech"})
        except Unavailable as e:
            counts["skipped"] += 1
            emit({"event": "skipped", "url": url, "reason": e.reason})
        except Blocked as e:
            blocked = True
            emit({"event": "blocked", "message": str(e)})
            break
        except Exception as e:  # YouTubeError or anything one odd video throws (ffmpeg, Whisper, PyAV): skip it only
            counts["skipped"] += 1
            emit({"event": "skipped", "url": url, "reason": f"error: {str(e)[:200]}"})
    result = ClipResult(blocked=blocked, **counts)
    emit({"event": "done", **result.__dict__})
    return result


_THAI = re.compile(r"[฀-๿]")


def import_text(library: ClipLibrary, *, url: str, text: str, title: str = "", creator: str = "",
                to: list[Path] = ()) -> Path:
    """A Clip whose transcript is a description written elsewhere (NexLev), one [00:00] line per paragraph."""
    key = parse_clip_url(url)
    if key is None:
        raise ValueError(f"not a YouTube / TikTok / Instagram clip URL: {url}")
    paragraphs = [" ".join(p.split()) for p in re.split(r"\n\s*\n", text) if p.strip()]
    old = library.read(key.key)
    targets = [str(Path(p).resolve()) for p in to]
    rec = VideoRecord(
        id=key.id, channel_id="", title=title or key.key, kind="short", published=date.today(), duration=0, url=url,
        lang="th" if _THAI.search(text) else "en", transcript_source="nexlev-description", status="active",
        summary_status="pending", topics=[], screen_frames=[], summary_md="(pending)", description="",
        transcript_lines=[f"[00:00] {p}" for p in paragraphs], platform=key.platform, creator=creator,
        display_name=old.display_name if old else None, copied_to=_merge(old.copied_to if old else [], targets),
    )
    return library.write(rec)
