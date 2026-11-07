import pathlib
from dataclasses import replace

import pytest

from brainsuck import clip as clip_module
from brainsuck.clip import clip, import_text
from brainsuck.library import ClipLibrary, LibraryConfig, clip_filename
from fakes import FakeTranscriber, FixtureClipSource

FIX = pathlib.Path(__file__).parent / "fixtures" / "clips"
TIKTOK = "https://www.tiktok.com/@garyvee/video/7479505763950611758"
YOUTUBE = "https://www.youtube.com/watch?v=3xU050kMbHM"
IG = "https://www.instagram.com/reels/DejxHqIpgBG/"
TT_KEY, YT_KEY, IG_KEY = "tiktok_7479505763950611758", "youtube_3xU050kMbHM", "instagram_DejxHqIpgBG"


@pytest.fixture
def env(tmp_path):
    lib = ClipLibrary(tmp_path / "คลัง mini")
    cache = tmp_path / "cache"
    tr = FakeTranscriber()
    src = FixtureClipSource(FIX)
    events = []

    def run(urls, source=None, transcriber=None, **kw):
        kw.setdefault("visual", False)
        return clip(urls, lib, source=source or src, make_transcriber=lambda: transcriber or tr, cache_dir=cache,
                    emit=events.append, **kw)

    return lib, cache, tr, src, events, run


def of(events, name):
    return [e for e in events if e["event"] == name]


def name_and_finish(lib, key, name="ชื่อที่ตั้ง", **kw):
    lib.write(replace(lib.read(key), summary_status="done", summary_md="สรุป", display_name=name, **kw))


def test_new_clips_written_pending(env):
    lib, cache, _, _, events, run = env
    result = run([TIKTOK, YOUTUBE, IG])
    assert (result.new, result.skipped, result.blocked) == (3, 0, False)
    records = [r for _, r in lib.iter_records()]
    assert len(records) == 3
    assert {r.platform for r in records} == {"tiktok", "youtube", "instagram"}
    assert all(r.summary_status == "pending" and r.display_name is None for r in records)
    assert events[0] == {"event": "start", "total": 3}
    assert events[-1]["event"] == "done"
    assert [e["status"] for e in of(events, "clip")] == ["new", "new", "new"]
    index = (lib.root / "index.md").read_text(encoding="utf-8")
    assert len([l for l in index.splitlines() if "(clips/" in l]) == 3
    assert not any((cache / "work").glob("*"))


def test_whisper_gets_prompt_and_lang(env):
    lib, _, tr, _, _, run = env
    run([YOUTUBE])
    assert tr.last_lang == "en"
    assert "How to Launch" in tr.last_prompt
    run([TIKTOK])
    assert tr.last_lang is None
    assert lib.read(TT_KEY).lang == "en"


def test_duplicate_url_reuses_record(env):
    _, _, tr, src, events, run = env
    run([YOUTUBE])
    calls, info = tr.calls, len(src.info_calls)
    run(["https://youtu.be/3xU050kMbHM?si=x"])
    assert of(events, "clip")[-1]["status"] == "existing"
    assert (tr.calls, len(src.info_calls)) == (calls, info)


def test_short_link_dedup_after_info(env):
    _, _, tr, _, events, run = env
    src = FixtureClipSource(FIX, aliases={"https://vm.tiktok.com/ZMabc/": TT_KEY})
    run([TIKTOK], source=src)
    calls = tr.calls
    run(["https://vm.tiktok.com/ZMabc/"], source=src)
    assert of(events, "clip")[-1]["status"] == "existing"
    assert tr.calls == calls


def test_same_url_twice_in_one_command(env):
    lib, _, _, _, events, run = env
    run([TIKTOK, TIKTOK + "?lang=en"])
    assert events[0] == {"event": "start", "total": 1}
    assert len(list(lib.iter_records())) == 1


def test_refresh_keeps_name_and_copies(env, tmp_path):
    lib, _, tr, _, events, run = env
    run([TIKTOK])
    name_and_finish(lib, TT_KEY, copied_to=[str(tmp_path / "ที่ปรึกษา")])
    calls = tr.calls
    result = run([TIKTOK], refresh=True)
    assert result.refreshed == 1
    assert of(events, "clip")[-1]["status"] == "refreshed"
    r = lib.read(TT_KEY)
    assert r.summary_status == "pending"
    assert r.display_name == "ชื่อที่ตั้ง"
    assert r.copied_to == [str(tmp_path / "ที่ปรึกษา")]
    assert tr.calls == calls + 1


def test_visual_frames_renamed_by_time(env, monkeypatch):
    lib, cache, _, _, _, run = env
    seen = {}

    def fake_frames(video, out_dir, threshold=0.4, max_frames=40):
        seen.update(threshold=threshold, max_frames=max_frames)
        out_dir.mkdir(parents=True, exist_ok=True)
        p = out_dir / "f00001.jpg"
        p.write_bytes(b"jpg")
        return [(12.6, p)]

    monkeypatch.setattr(clip_module, "extract_scene_frames", fake_frames)
    run([TIKTOK], visual=True)
    frame = cache / "frames" / TT_KEY / "t00012.jpg"
    assert lib.read(TT_KEY).screen_frames == [str(frame)]
    assert frame.exists()
    assert seen == {"threshold": 0.3, "max_frames": 40}


def test_no_visual_has_no_frames(env):
    lib, _, _, _, _, run = env
    run([TIKTOK], visual=False)
    assert lib.read(TT_KEY).screen_frames == []


def test_unclear_lines_set_quality(env):
    lib, _, _, _, _, run = env
    run([TIKTOK], transcriber=FakeTranscriber(low_conf_files={f"{TT_KEY}.audio.m4a"}))
    r = lib.read(TT_KEY)
    assert r.transcript_quality == 0.5
    assert r.transcript_lines[1].endswith("⟨ถอดไม่ชัด⟩")


def test_duration_falls_back_to_segments(env):
    lib, _, _, _, _, run = env
    run([IG])
    assert lib.read(IG_KEY).duration == 40


def test_ig_needs_login_event(env):
    lib, _, _, _, events, run = env
    result = run([IG], source=FixtureClipSource(FIX, needs_login={IG_KEY}))
    assert of(events, "needs-login") == [{"event": "needs-login", "url": IG, "key": IG_KEY, "tried": []}]
    assert result.needs_login == 1
    assert lib.read(IG_KEY) is None


def test_ig_cookies_auto_order_and_remember(env):
    lib, _, _, _, events, run = env
    src = FixtureClipSource(FIX, needs_login={IG_KEY}, cookie_ok={"firefox"})
    run([IG], source=src, ig_cookies="auto", remember=True)
    assert src.info_calls == [(IG, None), (IG, "edge"), (IG, "firefox")]
    assert lib.read(IG_KEY) is not None
    assert of(events, "clip")[-1]["cookies"] == "firefox"
    assert lib.load_config() == LibraryConfig("always", "firefox")


def test_config_always_uses_saved_browser(env):
    lib, _, _, _, _, run = env
    lib.save_config(LibraryConfig("always", "firefox"))
    src = FixtureClipSource(FIX, needs_login={IG_KEY}, cookie_ok={"firefox"})
    run([IG], source=src)
    assert src.info_calls == [(IG, None), (IG, "firefox")]
    assert lib.read(IG_KEY) is not None


def test_cookies_never_for_youtube(env):
    _, _, _, _, events, run = env
    src = FixtureClipSource(FIX, needs_login={YT_KEY})
    result = run([YOUTUBE], source=src, ig_cookies="auto")
    assert all(cookies is None for _, cookies in src.info_calls)
    assert result.skipped == 1
    assert of(events, "needs-login") == []


def test_bad_url_skipped_others_continue(env):
    lib, _, _, _, events, run = env
    result = run(["https://www.facebook.com/watch/?v=1", TIKTOK])
    assert of(events, "skipped") == [{"event": "skipped", "url": "https://www.facebook.com/watch/?v=1",
                                      "reason": "unsupported"}]
    assert (result.new, result.skipped) == (1, 1)
    assert lib.read(TT_KEY) is not None


def test_blocked_stops_batch(env):
    lib, _, _, _, events, run = env
    src = FixtureClipSource(FIX, blocked={TT_KEY})
    result = run([YOUTUBE, TIKTOK, IG], source=src)
    assert result.blocked is True
    assert lib.read(YT_KEY) is not None
    assert IG not in [u for u, _ in src.info_calls]
    assert of(events, "blocked")


def test_no_speech_skipped(env):
    lib, _, _, _, events, run = env
    run([TIKTOK], transcriber=FakeTranscriber(empty_files={f"{TT_KEY}.audio.m4a"}))
    assert of(events, "skipped")[0]["reason"] == "no-speech"
    assert lib.read(TT_KEY) is None


def test_to_existing_named_clip_copies_now(env, tmp_path):
    lib, _, _, _, _, run = env
    advisor = tmp_path / "ที่ปรึกษา ทดสอบ"
    advisor.mkdir()
    run([TIKTOK])
    name_and_finish(lib, TT_KEY)
    run([TIKTOK], to=[advisor])
    r = lib.read(TT_KEY)
    assert r.copied_to == [str(advisor.resolve())]
    assert (advisor / "clips" / clip_filename(r)).exists()


def test_import_text_creates_record(env):
    lib, _, _, _, _, _ = env
    path = import_text(lib, url=IG, text="ย่อหน้า1\n\nย่อหน้า2\n", title="ตัดต่อด้วย Claude", creator="colofill")
    r = lib.read(IG_KEY)
    assert path == lib.path_of(IG_KEY)
    assert r.transcript_lines == ["[00:00] ย่อหน้า1", "[00:00] ย่อหน้า2"]
    assert r.transcript_source == "nexlev-description"
    assert (r.lang, r.kind, r.summary_status, r.platform) == ("th", "short", "pending", "instagram")


class _CrashOn(FakeTranscriber):
    def transcribe_clip(self, audio, lang, prompt):
        if audio.name == f"{TT_KEY}.audio.m4a":
            raise ValueError("'en-US' is not a valid language code")
        return super().transcribe_clip(audio, lang, prompt)


def test_unexpected_error_skips_clip_not_batch(env):
    lib, _, _, _, events, run = env
    result = run([TIKTOK, YOUTUBE], transcriber=_CrashOn())
    assert of(events, "skipped")[0]["reason"].startswith("error:")
    assert (result.new, result.skipped) == (1, 1)
    assert events[-1]["event"] == "done"


def test_repaste_keeps_hand_edits(env):
    lib, _, _, _, _, run = env
    run([TIKTOK])
    path = lib.path_of(TT_KEY)
    notes = "\n## My notes\nโน้ตของฉัน\n"
    path.write_text(path.read_text(encoding="utf-8") + notes, encoding="utf-8")
    run([TIKTOK])
    assert "โน้ตของฉัน" in path.read_text(encoding="utf-8")
