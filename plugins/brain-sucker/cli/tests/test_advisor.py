import json

import pytest

from brainsuck.advisor import AdvisorMissing, channel_folder_name, ensure_advisor, update_channel_list


def test_creates_claude_md_with_domain(tmp_path):
    ensure_advisor(tmp_path, "ทำอาหาร")
    text = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert "ทำอาหาร" in text
    assert "brain-sucker:advisor" in text
    assert "<!-- brain-sucker:channels:start -->" in text


def test_requires_domain_for_new_advisor(tmp_path):
    with pytest.raises(AdvisorMissing):
        ensure_advisor(tmp_path, None)


def test_existing_advisor_untouched(tmp_path):
    ensure_advisor(tmp_path, "ทำอาหาร")
    p = tmp_path / "CLAUDE.md"
    p.write_text(p.read_text(encoding="utf-8") + "\nโน้ตของผู้ใช้\n", encoding="utf-8")
    ensure_advisor(tmp_path, None)
    assert "โน้ตของผู้ใช้" in p.read_text(encoding="utf-8")


def test_foreign_claude_md_gets_advisor_section_appended(tmp_path):
    p = tmp_path / "CLAUDE.md"
    p.write_text("# my own notes\n", encoding="utf-8")
    with pytest.raises(AdvisorMissing):
        ensure_advisor(tmp_path, None)
    ensure_advisor(tmp_path, "ทำอาหาร")
    text = p.read_text(encoding="utf-8")
    assert text.startswith("# my own notes")
    assert "brain-sucker:advisor" in text


def test_update_channel_list(tmp_path):
    ensure_advisor(tmp_path, "ทำอาหาร")
    ch = tmp_path / "channels" / "nickskitchen"
    ch.mkdir(parents=True)
    (ch / "state.json").write_text(json.dumps({
        "channel_id": "UC1", "handle": "@NicksKitchen", "folder": "nickskitchen", "title": "Nick's Kitchen",
        "known": {"a": {"id": "a", "title": "t", "status": "active"},
                  "b": {"id": "b", "title": "t", "status": "removed"}},
        "skipped": {}}), encoding="utf-8")
    update_channel_list(tmp_path)
    update_channel_list(tmp_path)
    text = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert text.count("Nick's Kitchen") == 1
    assert "@NicksKitchen" in text and "channels/nickskitchen" in text and "1 คลิป" in text


@pytest.mark.parametrize("handle, cid, expected", [
    ("@NicksKitchen", "UC1", "nickskitchen"),
    ("@ครัว:บ้าน", "UC1", "ครัว-บ้าน"),
    (None, "UC2HNqPgeKtVr2gZmLeeIk3g", "UC2HNqPgeKtVr2gZmLeeIk3g"),
    ("@", "UCx", "UCx"),
    ("@trailing.", "UC1", "trailing"),
])
def test_channel_folder_name(handle, cid, expected):
    assert channel_folder_name(handle, cid) == expected
