"""Ingest: turn a Channel into Channel Knowledge inside an Advisor. Incremental, resumable, idempotent."""
import shutil
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from brainsuck.advisor import channel_folder_name, ensure_advisor, update_channel_list
from brainsuck.frames import extract_scene_frames
from brainsuck.models import VideoRecord
from brainsuck.record import mark_removed, refresh_metadata
from brainsuck.store import ChannelState, ChannelStore
from brainsuck.sync import KnownVideo, plan_sync
from brainsuck.transcribe import Transcriber
from brainsuck.transcript import WHISPER, choose_source, format_lines
from brainsuck.youtube import Blocked, Unavailable, YouTube


@dataclass(frozen=True)
class IngestResult:
    new: int
    refreshed: int
    removed: int
    skipped: int
    blocked: bool


class _NoSpeech(Exception):
    pass


def _find_state(advisor_dir: Path, channel_id: str) -> ChannelState | None:
    for state_file in (advisor_dir / "channels").glob("*/state.json"):
        s = ChannelStore(state_file.parent).load_state()
        if s and s.channel_id == channel_id:
            return s
    return None


def _new_folder(advisor_dir: Path, handle: str | None, channel_id: str) -> str:
    base = channel_folder_name(handle, channel_id)
    name, n = base, 2
    while (advisor_dir / "channels" / name).exists():
        name, n = f"{base}-{n}", n + 1
    return name


def ingest(channel_id: str, advisor_dir: Path, *, yt: YouTube, make_transcriber: Callable[[], Transcriber],
           cache_dir: Path, domain: str | None = None, screen_text: bool = False, limit: int | None = None,
           emit: Callable[[dict], None] = lambda e: None) -> IngestResult:
    ensure_advisor(advisor_dir, domain)
    channel, refs = yt.list_channel(channel_id)
    state = _find_state(advisor_dir, channel_id) or ChannelState(
        channel_id, channel.handle, _new_folder(advisor_dir, channel.handle, channel_id), channel.title, {}, {})
    store = ChannelStore(advisor_dir / "channels" / state.folder)
    plan = plan_sync(refs, state.known, set(state.skipped))
    listed_title = {r.id: r.title for r in refs}
    known, skipped = dict(state.known), dict(state.skipped)

    def save() -> None:
        store.save_state(replace(state, title=channel.title, known=known, skipped=skipped))

    for vid, status in [(v, "removed") for v in plan.removed] + [(v, "active") for v in plan.restored]:
        r = store.read_record(vid)
        if r:
            store.write_record(mark_removed(r) if status == "removed" else replace(r, status="active"))
        known[vid] = replace(known[vid], status=status)
    save()

    transcriber: list[Transcriber] = []
    refreshed = new = n_skipped = 0
    blocked = False
    todo = plan.new[:limit] if limit else plan.new
    emit({"event": "start", "total_new": len(todo)})
    try:
        for vid in plan.refresh:
            r = store.read_record(vid)
            try:
                info = yt.fetch_info(vid)
            except Unavailable:
                continue
            if r:
                store.write_record(refresh_metadata(r, info))
            known[vid] = replace(known[vid], title=listed_title[vid])
            refreshed += 1
            save()
        for i, vid in enumerate(todo, 1):
            work = cache_dir / "work" / vid
            try:
                rec = _build_record(vid, yt, transcriber, make_transcriber, cache_dir, work, screen_text)
            except (Unavailable, _NoSpeech) as e:
                reason = e.reason if isinstance(e, Unavailable) else "no-speech"
                skipped[vid] = reason
                n_skipped += 1
                save()
                emit({"event": "skipped", "id": vid, "reason": reason})
                continue
            finally:
                shutil.rmtree(work, ignore_errors=True)
            store.write_record(rec)
            known[vid] = KnownVideo(vid, listed_title[vid], "active")
            new += 1
            save()
            emit({"event": "video", "id": vid, "source": rec.transcript_source, "i": i, "n": len(todo)})
    except Blocked as e:
        save()
        blocked = True
        emit({"event": "blocked", "message": str(e)})
    store.write_index()
    store.write_skipped()
    update_channel_list(advisor_dir)
    result = IngestResult(new=new, refreshed=refreshed, removed=len(plan.removed), skipped=n_skipped,
                          blocked=blocked)
    emit({"event": "done", **result.__dict__})
    return result


def _build_record(vid: str, yt: YouTube, transcriber: list[Transcriber], make_transcriber, cache_dir: Path,
                  work: Path, screen_text: bool) -> VideoRecord:
    info = yt.fetch_info(vid)
    source, key = choose_source(info.lang, info.captions)
    segments = yt.fetch_captions(vid, key) if key else []
    if not segments:
        source = WHISPER
        if not transcriber:
            transcriber.append(make_transcriber())
        segments = transcriber[0].transcribe(yt.fetch_audio(vid, work), info.lang)
    if not segments:
        raise _NoSpeech()
    frames: list[str] = []
    if screen_text:
        video = yt.fetch_video_360p(vid, work)
        frames = [str(p) for _, p in extract_scene_frames(video, cache_dir / "frames" / vid)]
    return VideoRecord(
        id=info.id, channel_id=info.channel_id, title=info.title, kind=info.kind, published=info.published,
        duration=info.duration, url=info.url, lang=info.lang, transcript_source=source, status="active",
        summary_status="pending", topics=[], screen_frames=frames, summary_md="(pending)",
        description=info.description, transcript_lines=format_lines(segments),
    )
