from datetime import date

import pytest

from brainsuck.store import ChannelState, ChannelStore
from brainsuck.sync import KnownVideo


@pytest.fixture
def store(tmp_path):
    return ChannelStore(tmp_path / "ที่ปรึกษา ทดสอบ" / "channels" / "nickskitchen")


def test_state_round_trip(store):
    s = ChannelState("UC1", "@NicksKitchen", "nickskitchen", "Nick's Kitchen",
                     known={"a": KnownVideo("a", "ซุป", "active")}, skipped={"b": "members-only"})
    store.save_state(s)
    assert store.load_state() == s


def test_load_state_missing_is_none(store):
    assert store.load_state() is None


def test_write_then_read_record(store, make_record):
    r = make_record(title="ซุปกระดูกหมู")
    path = store.write_record(r)
    assert path.name == "2026-10-01_K_SXQoMdSf4.md"
    assert store.read_record("K_SXQoMdSf4") == r
    assert store.read_record("nope") is None


def test_index_order_and_removed_label(store, make_record):
    store.write_record(make_record(id="old", title="Old", published=date(2025, 1, 1)))
    store.write_record(make_record(id="new", title="New", published=date(2026, 1, 1), kind="short",
                                   summary_status="done"))
    store.write_record(make_record(id="gone", title="Gone", published=date(2025, 6, 1), status="removed"))
    store.write_index()
    rows = [l for l in (store.channel_dir / "index.md").read_text(encoding="utf-8").splitlines()
            if l.startswith("| 20")]
    assert [r.split("|")[3].strip() for r in rows] == ["New", "Gone (ลบแล้ว)", "Old"]
    assert "short" in rows[0] and "✓" in rows[0]


def test_skipped_file(store):
    store.save_state(ChannelState("UC1", None, "uc1", "X", known={}, skipped={"abc": "members-only"}))
    store.write_skipped()
    text = (store.channel_dir / "skipped.md").read_text(encoding="utf-8")
    assert "abc" in text and "members-only" in text and "https://www.youtube.com/watch?v=abc" in text


def test_no_tmp_left_after_write(store, make_record):
    store.write_record(make_record())
    store.save_state(ChannelState("UC1", None, "uc1", "X", known={}, skipped={}))
    assert not list(store.channel_dir.rglob("*.tmp"))


def test_leftover_tmp_ignored_by_iter_records(store, make_record):
    store.write_record(make_record())
    (store.channel_dir / "videos" / "2026-10-02_half.tmp").write_text("---\nbroken", encoding="utf-8")
    assert [r.id for r in store.iter_records()] == ["K_SXQoMdSf4"]
