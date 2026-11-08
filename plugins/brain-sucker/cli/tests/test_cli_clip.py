import json
import pathlib

import pytest

from brainsuck.cli import main
from brainsuck.library import ClipLibrary
from fakes import FakeTranscriber, FixtureClipSource

FIX = pathlib.Path(__file__).parent / "fixtures" / "clips"
TIKTOK = "https://www.tiktok.com/@garyvee/video/7479505763950611758"
YOUTUBE = "https://www.youtube.com/watch?v=3xU050kMbHM"
IG = "https://www.instagram.com/reels/DejxHqIpgBG/"
TT_KEY = "tiktok_7479505763950611758"


@pytest.fixture(autouse=True)
def cache(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAINSUCK_CACHE", str(tmp_path / "cache"))
    monkeypatch.delenv("BRAINSUCK_LIBRARY", raising=False)


@pytest.fixture
def lib(tmp_path):
    return tmp_path / "คลัง mini"


def run(argv, src=None):
    return main(argv, clip_source=src or FixtureClipSource(FIX), make_transcriber=FakeTranscriber)


def json_lines(out):
    return [json.loads(l) for l in out.splitlines() if l.strip()]


def test_clip_cmd_streams_json(lib, capsys):
    assert run(["clip", TIKTOK, YOUTUBE, "--no-visual", "--library", str(lib)]) == 0
    events = json_lines(capsys.readouterr().out)
    assert events[0] == {"event": "start", "total": 2}
    assert events[-1]["event"] == "done" and events[-1]["new"] == 2


def test_clip_to_non_advisor_exit3(lib, tmp_path, capsys):
    src = FixtureClipSource(FIX)
    not_advisor = tmp_path / "ไม่ใช่ที่ปรึกษา"
    not_advisor.mkdir()
    code = run(["clip", TIKTOK, "--no-visual", "--library", str(lib), "--to", str(not_advisor)], src)
    assert code == 3
    assert json_lines(capsys.readouterr().out)[-1]["kind"] == "not-an-advisor"
    assert src.info_calls == []


def test_clip_to_advisor_ok(lib, tmp_path, capsys):
    advisor = tmp_path / "ที่ปรึกษา ทดสอบ"
    advisor.mkdir()
    (advisor / "CLAUDE.md").write_text("<!-- brain-sucker:advisor -->\n", encoding="utf-8")
    assert run(["clip", TIKTOK, "--no-visual", "--library", str(lib), "--to", str(advisor)]) == 0
    assert ClipLibrary(lib).read(TT_KEY).copied_to == [str(advisor.resolve())]


def test_clip_name_renames(lib, capsys):
    run(["clip", TIKTOK, "--no-visual", "--library", str(lib)])
    capsys.readouterr()
    assert run(["clip-name", TT_KEY, "ขายของให้คนรวย", "--library", str(lib)]) == 0
    event = json_lines(capsys.readouterr().out)[-1]
    assert event["event"] == "named"
    assert pathlib.Path(event["path"]).name == f"{TT_KEY}__ขายของให้คนรวย.md"
    assert pathlib.Path(event["path"]).exists()


def test_clip_name_unknown_exit1(lib, capsys):
    assert run(["clip-name", "tiktok_nope", "x", "--library", str(lib)]) == 1
    assert json_lines(capsys.readouterr().out)[-1]["kind"] == "unknown-clip"


def test_clip_name_bad_name_exit1(lib, capsys):
    run(["clip", TIKTOK, "--no-visual", "--library", str(lib)])
    capsys.readouterr()
    assert run(["clip-name", TT_KEY, "???", "--library", str(lib)]) == 1
    assert json_lines(capsys.readouterr().out)[-1]["kind"] == "bad-name"


def test_clip_import_from_file(lib, tmp_path, capsys):
    text = tmp_path / "คำบรรยาย nexlev.txt"
    text.write_text("ใช้ Claude ตัดต่อ\n\nขั้นที่สอง", encoding="utf-8")
    assert run(["clip-import", "--url", IG, "--text-file", str(text), "--title", "ตัดต่อ", "--library",
                str(lib)]) == 0
    event = json_lines(capsys.readouterr().out)[-1]
    assert (event["event"], event["status"]) == ("clip", "new")
    assert ClipLibrary(lib).read(event["key"]).transcript_source == "nexlev-description"


def test_clip_status_json(lib, capsys):
    run(["clip", TIKTOK, YOUTUBE, IG, "--no-visual", "--library", str(lib)])
    capsys.readouterr()
    assert run(["clip-status", "--library", str(lib)]) == 0
    s = json.loads(capsys.readouterr().out)
    assert len(s["pending"]) == 3
    assert s["unnamed"] == []


def test_library_from_env(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("BRAINSUCK_LIBRARY", str(tmp_path / "คลัง"))
    assert run(["clip-status"]) == 0
    assert json.loads(capsys.readouterr().out)["library"] == str((tmp_path / "คลัง").resolve())


def test_exit_blocked(lib, capsys):
    src = FixtureClipSource(FIX, blocked={TT_KEY})
    assert run(["clip", TIKTOK, "--no-visual", "--library", str(lib)], src) == 2
