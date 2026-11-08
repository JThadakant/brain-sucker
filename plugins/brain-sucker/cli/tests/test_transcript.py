import json
import pathlib

from brainsuck.models import Segment
from brainsuck.transcript import (choose_source, detect_lang, format_lines, parse_json3, transcript_quality,
                                  whisper_prompt)

FIX = pathlib.Path(__file__).parent / "fixtures" / "captions"


def test_thai_always_whisper():
    assert choose_source("th", {"th": "auto", "th-orig": "auto"}) == ("whisper-large-v3", None)


def test_manual_beats_auto():
    assert choose_source("en", {"en": "manual", "en-orig": "auto"}) == ("youtube-manual", "en")


def test_orig_auto():
    assert choose_source("en", {"en-orig": "auto", "en": "auto"}) == ("youtube-auto", "en-orig")


def test_no_captions_falls_back_to_whisper():
    assert choose_source("en", {}) == ("whisper-large-v3", None)


def test_parse_json3_strips_music():
    segs = parse_json3(json.loads((FIX / "chocolate.en-orig.json3").read_text(encoding="utf-8")))
    text = " ".join(s.text for s in segs)
    assert "[music]" not in text.lower()
    assert ">>" not in text
    assert "  " not in text
    assert segs[0].start < 1
    assert "chocolate" in text


def test_format_lines():
    segs = [Segment(0, "a"), Segment(12, "b"), Segment(31, "c"), Segment(3700, "d")]
    assert format_lines(segs) == ["[00:00] a b", "[00:31] c", "[1:01:40] d"]


def test_detect_lang_from_orig():
    assert detect_lang({"automatic_captions": {"th-orig": [], "en": []}}) == "th"


def test_detect_lang_prefers_language_field():
    assert detect_lang({"language": "en", "automatic_captions": {"th-orig": []}}) == "en"


def test_detect_lang_default_en():
    assert detect_lang({}) == "en"


def test_unclear_marker_on_line():
    segs = [Segment(0, "a"), Segment(10, "b", low_conf=True), Segment(40, "c")]
    assert format_lines(segs) == ["[00:00] a b ⟨ถอดไม่ชัด⟩", "[00:40] c"]


def test_quality_share():
    lines = ["[00:00] a ⟨ถอดไม่ชัด⟩", "[00:30] b", "[01:00] c", "[01:30] d"]
    assert transcript_quality(lines) == 0.25
    assert transcript_quality([]) == 0.0


def test_prompt_strips_urls_and_hashtags():
    got = whisper_prompt("How to Launch", "Y Combinator", "Kat Mañalac https://yc.com #startup tips")
    assert got == "How to Launch. Y Combinator. Kat Mañalac tips"


def test_prompt_capped_300():
    assert len(whisper_prompt("t", "c", "ก" * 1000)) <= 300


def test_prompt_skips_empty():
    assert whisper_prompt("", "garyvee", "") == "garyvee"
