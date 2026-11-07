from dataclasses import replace
from datetime import date

from brainsuck.models import VideoInfo, VideoRecord
from brainsuck.record import mark_removed, parse_record, record_filename, refresh_metadata, render_record


def make_record(**kw) -> VideoRecord:
    base = dict(
        id="K_SXQoMdSf4",
        channel_id="UC2HNqPgeKtVr2gZmLeeIk3g",
        title='ซุปกระดูกหมู: เคล็ดลับ "ใส" แบบเชฟ',
        kind="long",
        published=date(2026, 10, 1),
        duration=368,
        url="https://www.youtube.com/watch?v=K_SXQoMdSf4",
        lang="th",
        transcript_source="whisper-large-v3",
        status="active",
        summary_status="pending",
        topics=[],
        screen_frames=[],
        summary_md="(pending)",
        description="คำอธิบาย\nบรรทัดสอง",
        transcript_lines=["[00:00] ล้างให้สะอาด", "[00:31] ต้มเลยนะครับ"],
    )
    base.update(kw)
    return VideoRecord(**base)


def make_info(**kw) -> VideoInfo:
    base = dict(
        id="K_SXQoMdSf4",
        channel_id="UC2HNqPgeKtVr2gZmLeeIk3g",
        title="New title",
        description="new description",
        published=date(2026, 10, 1),
        duration=370,
        kind="long",
        url="https://www.youtube.com/watch?v=K_SXQoMdSf4",
        lang="th",
        captions={},
    )
    base.update(kw)
    return VideoInfo(**base)


def test_round_trip():
    r = make_record(topics=["ซุป", "กระดูก"], screen_frames=["C:/cache/f1.jpg"])
    assert parse_record(render_record(r)) == r


def test_round_trip_with_screen_text():
    r = make_record(screen_text_lines=["[00:08] เทคนิคที่ 1"])
    assert parse_record(render_record(r)) == r


def test_filename():
    assert record_filename(make_record()) == "2026-10-01_K_SXQoMdSf4.md"


def test_refresh_keeps_summary():
    r = make_record(summary_status="done", summary_md="สรุปเดิม", topics=["stew"])
    out = refresh_metadata(r, make_info())
    assert out.title == "New title"
    assert out.description == "new description"
    assert out.duration == 370
    assert out.summary_md == "สรุปเดิม"
    assert out.topics == ["stew"]
    assert out.transcript_lines == r.transcript_lines
    assert out.summary_status == "done"


def test_mark_removed():
    r = make_record()
    assert mark_removed(r) == replace(r, status="removed")


def test_description_with_heading_lines_round_trips():
    r = make_record(description="intro\n## Ingredients\n- beef\n## Transcript\nfake")
    assert parse_record(render_record(r)) == r
