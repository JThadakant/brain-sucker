from dataclasses import replace
from datetime import date

import pytest

from brainsuck.library import ClipLibrary, LibraryConfig, clip_filename, library_status, slugify


@pytest.fixture
def clip(make_record):
    def _make(**kw):
        base = dict(id="3xU050kMbHM", channel_id="", platform="youtube", title="Kat Mañalac - How to Launch",
                    creator="Y Combinator", transcript_source="whisper-large-v3")
        base.update(kw)
        return make_record(**base)
    return _make


@pytest.fixture
def lib(tmp_path):
    return ClipLibrary(tmp_path / "mini brain คลัง")


def done(r, name):
    return replace(r, summary_status="done", summary_md="สรุป", topics=["launch", "startup"], display_name=name)


def test_slugify_rules():
    assert slugify("How to Launch: YC/Kat?") == "How-to-Launch-YC-Kat"
    assert slugify("ขายของ ให้คนรวย 💰") == "ขายของ-ให้คนรวย-💰"
    assert len(slugify("a" * 100)) == 60
    assert slugify("???") == ""


def test_filename_unnamed_and_named(clip):
    r = clip()
    assert clip_filename(r) == "youtube_3xU050kMbHM.md"
    assert clip_filename(replace(r, display_name="How to Launch")) == "youtube_3xU050kMbHM__How-to-Launch.md"


def test_rename_removes_old_file(lib, clip):
    lib.write(clip())
    lib.write(done(clip(), "How to Launch"))
    assert [p.name for p in lib.clips_dir.glob("*.md")] == ["youtube_3xU050kMbHM__How-to-Launch.md"]


def test_same_name_two_clips(lib, clip):
    lib.write(done(clip(), "เปิดตัว"))
    lib.write(done(clip(id="7479505763950611758", platform="tiktok"), "เปิดตัว"))
    assert len(list(lib.clips_dir.glob("*.md"))) == 2
    assert lib.read("tiktok_7479505763950611758").platform == "tiktok"
    assert lib.read("youtube_3xU050kMbHM").platform == "youtube"


def test_path_of_ignores_lookalike_ids(lib, clip):
    lib.write(clip(id="Dej", platform="instagram"))
    lib.write(clip(id="Dej__x", platform="instagram"))
    assert lib.read("instagram_Dej").id == "Dej"
    assert lib.read("instagram_Dej__x").id == "Dej__x"
    assert lib.path_of("instagram_nope") is None


def test_copies_only_when_done_and_named(lib, clip, tmp_path):
    advisor = tmp_path / "ที่ปรึกษา ทดสอบ"
    advisor.mkdir()
    r = clip(copied_to=[str(advisor)])
    lib.write(r)
    assert not (advisor / "clips").exists()
    path = lib.write(done(r, "How to Launch"))
    copy = advisor / "clips" / path.name
    assert copy.read_text(encoding="utf-8") == path.read_text(encoding="utf-8")
    lib.write(done(r, "เปิดตัวซ้ำๆ"))
    assert [p.name for p in (advisor / "clips").glob("*.md")] == ["youtube_3xU050kMbHM__เปิดตัวซ้ำๆ.md"]


def test_copy_skips_missing_advisor(lib, clip, tmp_path):
    gone = tmp_path / "หายไปแล้ว"
    lib.write(done(clip(copied_to=[str(gone)]), "x"))
    assert not gone.exists()


def test_index_rows(lib, clip):
    lib.write(clip(id="7479505763950611758", platform="tiktok", title="Simple things", creator="garyvee",
                   published=date(2025, 3, 9)))
    lib.write(done(clip(), "Launch | ซ้ำๆ"))
    lines = (lib.root / "index.md").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# Clip Library"
    assert "| ชื่อ | แพลตฟอร์ม | ผู้สร้าง | วันที่ | แท็ก | ไฟล์ |" in lines
    rows = [l for l in lines if l.startswith("| ") and "clips/" in l]
    assert len(rows) == 2
    assert rows[0].startswith(r"| Launch \| ซ้ำๆ | youtube | Y Combinator | 2026-10-01 | launch, startup | [")
    assert "Simple things (รอสรุป)" in rows[1]
    assert "(clips/tiktok_7479505763950611758.md)" in rows[1]


def test_config_defaults_and_save(lib):
    assert lib.load_config() == LibraryConfig("ask", None)
    lib.save_config(LibraryConfig("always", "firefox"))
    assert lib.load_config() == LibraryConfig("always", "firefox")


def test_status_pending_and_unnamed(lib, clip):
    p = lib.write(clip(id="7479505763950611758", platform="tiktok"))
    lib.write(replace(clip(), summary_status="done"))
    s = library_status(lib)
    assert s["library"] == str(lib.root.resolve())
    assert s["clips"] == 2
    assert s["pending"] == [str(p.resolve())]
    assert s["unnamed"] == ["youtube_3xU050kMbHM"]
    assert s["config"] == {"ig_cookies": "ask", "browser": None}


def test_status_reports_stale_copies(lib, clip, tmp_path):
    advisor = tmp_path / "ที่ปรึกษา"
    advisor.mkdir()
    path = lib.write(done(clip(copied_to=[str(advisor)]), "Launch"))
    assert library_status(lib)["stale_copies"] == []
    path.write_text(path.read_text(encoding="utf-8").replace("สรุป", "สรุปใหม่หลัง refresh"), encoding="utf-8")
    assert library_status(lib)["stale_copies"] == ["youtube_3xU050kMbHM"]
