import json
import pathlib

import pytest

from brainsuck.cli import main
from fakes import FakeTranscriber, FixtureYouTube

FIX = pathlib.Path(__file__).parent / "fixtures" / "youtube"
CID = "UC2HNqPgeKtVr2gZmLeeIk3g"


@pytest.fixture(autouse=True)
def cache(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAINSUCK_CACHE", str(tmp_path / "cache"))


def run(argv, yt=None):
    return main(argv, yt=yt or FixtureYouTube(FIX), make_transcriber=FakeTranscriber)


def json_lines(out):
    return [json.loads(l) for l in out.splitlines() if l.strip()]


def test_resolve_prints_candidates(capsys):
    assert run(["resolve", "@NicksKitchen"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["channel_id"] == CID


def test_ingest_ok_streams_json_lines(tmp_path, capsys):
    advisor = tmp_path / "ที่ปรึกษา ทำอาหาร"
    assert run(["ingest", CID, "--advisor", str(advisor), "--domain", "ทำอาหาร"]) == 0
    events = json_lines(capsys.readouterr().out)
    assert events[0]["event"] == "start" and events[-1]["event"] == "done"


def test_ingest_exit_code_blocked(tmp_path, capsys):
    code = run(["ingest", CID, "--advisor", str(tmp_path / "a"), "--domain", "x"],
               yt=FixtureYouTube(FIX, blocked_after=1))
    assert code == 2
    assert "blocked" in [e["event"] for e in json_lines(capsys.readouterr().out)]


def test_ingest_exit_code_missing_domain(tmp_path, capsys):
    assert run(["ingest", CID, "--advisor", str(tmp_path / "a")]) == 3
    assert json_lines(capsys.readouterr().out)[-1]["event"] == "error"


def test_ingest_exit_code_suspicious_listing(tmp_path, capsys):
    advisor = str(tmp_path / "a")
    run(["ingest", CID, "--advisor", advisor, "--domain", "x"])
    every = {"K_SXQoMdSf4", "cM5IAypOOfM", "LexQiGdPlxU", "wrZZf2ER3ak", "MEMBERS0001"}
    assert run(["ingest", CID, "--advisor", advisor], yt=FixtureYouTube(FIX, drop=every)) == 4


def test_status_pending_and_needs_synthesis(tmp_path, capsys):
    advisor = tmp_path / "ที่ปรึกษา ทำอาหาร"
    run(["ingest", CID, "--advisor", str(advisor), "--domain", "ทำอาหาร"])
    capsys.readouterr()
    assert run(["status", str(advisor)]) == 0
    out = capsys.readouterr().out
    ch = json.loads(out)["channels"][0]
    assert ch["folder"] == "nickskitchen" and ch["videos"] == 4 and ch["skipped"] == 1
    assert len(ch["pending"]) == 4 and all(pathlib.Path(p).exists() for p in ch["pending"])
    assert ch["needs_synthesis"] is False
    assert "ทำอาหาร" in out and "\\u0e" not in out


def test_status_needs_synthesis_after_summaries(tmp_path, capsys):
    from brainsuck.status import collect_status

    advisor = tmp_path / "a"
    run(["ingest", CID, "--advisor", str(advisor), "--domain", "x"])
    pending = collect_status(advisor)["channels"][0]["pending"]
    p = pathlib.Path(pending[0])
    p.write_text(p.read_text(encoding="utf-8").replace("summary: pending", "summary: done"), encoding="utf-8")
    ch = collect_status(advisor)["channels"][0]
    assert ch["needs_synthesis"] is True and len(ch["pending"]) == 3
    (advisor / "channels" / "nickskitchen" / "topics.md").write_text("---\ncovers: 1\n---\n# Topics\n",
                                                                   encoding="utf-8")
    assert collect_status(advisor)["channels"][0]["needs_synthesis"] is False
