import pathlib
from dataclasses import replace

import pytest

from brainsuck import ingest as ingest_module
from brainsuck.advisor import AdvisorMissing
from brainsuck.ingest import IngestResult, ingest
from brainsuck.record import parse_record, render_record
from brainsuck.store import ChannelStore
from brainsuck.sync import SuspiciousListing
from fakes import FakeTranscriber, FixtureYouTube

FIX = pathlib.Path(__file__).parent / "fixtures" / "youtube"
CID = "UC2HNqPgeKtVr2gZmLeeIk3g"


@pytest.fixture
def env(tmp_path):
    advisor = tmp_path / "ที่ปรึกษา ทำอาหาร"
    cache = tmp_path / "cache"
    tr = FakeTranscriber()
    events = []

    def run(yt=None, **kw):
        kw.setdefault("domain", "ทำอาหาร")
        return ingest(CID, advisor, yt=yt or FixtureYouTube(FIX), make_transcriber=lambda: tr,
                      cache_dir=cache, emit=events.append, **kw)

    return advisor, cache, tr, events, run


def store(advisor):
    return ChannelStore(advisor / "channels" / "nickskitchen")


def test_first_ingest_creates_advisor_and_records(env):
    advisor, _, _, events, run = env
    result = run()
    assert result == IngestResult(new=4, refreshed=0, removed=0, skipped=1, blocked=False)
    assert len(list((advisor / "channels" / "nickskitchen" / "videos").glob("*.md"))) == 4
    assert "ทำอาหาร" in (advisor / "CLAUDE.md").read_text(encoding="utf-8")
    index = (advisor / "channels" / "nickskitchen" / "index.md").read_text(encoding="utf-8")
    assert len([l for l in index.splitlines() if l.startswith("| 20")]) == 4
    assert events[0] == {"event": "start", "total_new": 5}
    assert events[-1]["event"] == "done"


def test_requires_domain_for_new_advisor(env):
    _, _, _, _, run = env
    with pytest.raises(AdvisorMissing):
        run(domain=None)


def test_thai_uses_whisper_english_uses_captions(env):
    advisor, _, tr, _, run = env
    run()
    s = store(advisor)
    assert s.read_record("LexQiGdPlxU").transcript_source == "whisper-large-v3"
    assert s.read_record("K_SXQoMdSf4").transcript_source == "youtube-manual"
    assert s.read_record("cM5IAypOOfM").transcript_source == "youtube-auto"
    assert s.read_record("wrZZf2ER3ak").kind == "short"
    assert tr.calls == 1
    assert s.read_record("cM5IAypOOfM").transcript_lines[0].startswith("[00:00] ")


def test_english_only_never_builds_transcriber(tmp_path):
    def boom():
        raise AssertionError("transcriber built for an English-only run")

    result = ingest(CID, tmp_path / "a", yt=FixtureYouTube(FIX, drop={"LexQiGdPlxU"}), make_transcriber=boom,
                    cache_dir=tmp_path / "c", domain="x")
    assert result.new == 3


def test_rerun_is_noop(env):
    advisor, _, _, _, run = env
    run()
    files = list((advisor / "channels" / "nickskitchen" / "videos").glob("*.md"))
    before = {f: f.stat().st_mtime_ns for f in files}
    assert run() == IngestResult(new=0, refreshed=0, removed=0, skipped=0, blocked=False)
    assert {f: f.stat().st_mtime_ns for f in files} == before


def test_blocked_midway_then_resume(env):
    advisor, _, _, events, run = env
    first = run(yt=FixtureYouTube(FIX, blocked_after=3))
    assert first.blocked and first.new == 2
    assert {"event": "blocked"} in [{"event": e["event"]} for e in events]
    assert len(store(advisor).load_state().known) == 2
    second = run()
    assert second.new == 2 and not second.blocked
    assert len(list(store(advisor).iter_records())) == 4


def test_unavailable_goes_to_skipped(env):
    advisor, _, _, events, run = env
    run()
    skipped = (advisor / "channels" / "nickskitchen" / "skipped.md").read_text(encoding="utf-8")
    assert "MEMBERS0001" in skipped and "members-only" in skipped
    assert store(advisor).read_record("MEMBERS0001") is None
    assert {"event": "skipped", "id": "MEMBERS0001", "reason": "members-only"} in events


def test_removed_marks_status(env):
    advisor, _, _, _, run = env
    run()
    result = run(yt=FixtureYouTube(FIX, drop={"cM5IAypOOfM"}))
    assert result.removed == 1
    assert store(advisor).read_record("cM5IAypOOfM").status == "removed"
    assert "(ลบแล้ว)" in (advisor / "channels" / "nickskitchen" / "index.md").read_text(encoding="utf-8")


def test_removed_video_restored_when_back(env):
    advisor, _, _, _, run = env
    run()
    run(yt=FixtureYouTube(FIX, drop={"cM5IAypOOfM"}))
    run()
    assert store(advisor).read_record("cM5IAypOOfM").status == "active"


def test_refresh_preserves_summary(env):
    advisor, _, _, _, run = env
    run()
    s = store(advisor)
    r = s.read_record("K_SXQoMdSf4")
    s.write_record(replace(r, summary_status="done", summary_md="สรุปเดิม"))
    result = run(yt=FixtureYouTube(FIX, titles={"K_SXQoMdSf4": "Beef Stew v2"}))
    assert result.refreshed == 1
    r2 = s.read_record("K_SXQoMdSf4")
    assert r2.title == "Beef Stew v2" and r2.summary_md == "สรุปเดิม" and r2.summary_status == "done"


def test_suspicious_listing_marks_nothing(env):
    advisor, _, _, _, run = env
    run()
    with pytest.raises(SuspiciousListing):
        run(yt=FixtureYouTube(FIX, drop={"K_SXQoMdSf4", "cM5IAypOOfM", "LexQiGdPlxU", "wrZZf2ER3ak",
                                         "MEMBERS0001"}))
    assert all(r.status == "active" for r in store(advisor).iter_records())


def test_cache_cleaned(env):
    _, cache, _, _, run = env
    run()
    assert not [p for p in cache.rglob("*") if p.is_file()]


def test_limit(env):
    advisor, _, _, _, run = env
    first = run(limit=2)
    assert (first.new, first.skipped) == (1, 1)
    assert run().new == 3


def test_screen_text_records_frames(env, monkeypatch, tmp_path):
    advisor, cache, _, _, run = env

    def fake_frames(video, out_dir, **kw):
        out_dir.mkdir(parents=True, exist_ok=True)
        f = out_dir / "f00001.jpg"
        f.write_bytes(b"jpg")
        return [(8.0, f)]

    monkeypatch.setattr(ingest_module, "extract_scene_frames", fake_frames)
    run(screen_text=True)
    r = store(advisor).read_record("K_SXQoMdSf4")
    assert len(r.screen_frames) == 1 and pathlib.Path(r.screen_frames[0]).exists()
    assert not list(cache.rglob("*.mp4"))


def test_second_channel_gets_own_folder_and_listed(env, tmp_path):
    advisor, _, _, _, run = env
    run()
    text = (advisor / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Nick's Kitchen" in text and "channels/nickskitchen" in text


def test_partial_tmp_file_from_crash_is_ignored_on_resume(env):
    advisor, _, _, _, run = env
    run(limit=1)
    videos = advisor / "channels" / "nickskitchen" / "videos"
    (videos / "2026-10-16_cM5IAypOOfM.md.tmp").write_text("---\nhalf", encoding="utf-8")
    run()
    assert len(list(store(advisor).iter_records())) == 4
    assert parse_record(render_record(store(advisor).read_record("cM5IAypOOfM"))).id == "cM5IAypOOfM"
