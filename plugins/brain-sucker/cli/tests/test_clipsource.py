import json
import pathlib

import pytest

from brainsuck.clipsource import (ClipKey, NeedsLogin, YtDlpClipSource, classify_clip_error, clip_info_from_ytdlp,
                                  parse_clip_url)
from brainsuck.youtube import Unavailable

FIX = pathlib.Path(__file__).parent / "fixtures" / "clips" / "info"
TIKTOK = "https://www.tiktok.com/@garyvee/video/7479505763950611758"
YOUTUBE = "https://www.youtube.com/watch?v=3xU050kMbHM"


def fixture(key: str) -> dict:
    return json.loads((FIX / f"{key}.json").read_text(encoding="utf-8"))


def test_parse_youtube_variants():
    for url in ["https://www.youtube.com/watch?v=3xU050kMbHM&t=5", "https://youtu.be/3xU050kMbHM?si=abc",
                "https://www.youtube.com/shorts/3xU050kMbHM", "https://m.youtube.com/watch?v=3xU050kMbHM"]:
        assert parse_clip_url(url) == ClipKey("youtube", "3xU050kMbHM"), url


def test_parse_tiktok():
    assert parse_clip_url(TIKTOK + "?lang=en") == ClipKey("tiktok", "7479505763950611758")
    assert parse_clip_url("https://vm.tiktok.com/ZMabc123/") is None


def test_parse_instagram():
    for url in ["https://www.instagram.com/reels/DejxHqIpgBG/", "https://www.instagram.com/reel/DejxHqIpgBG/?igsh=x",
                "https://www.instagram.com/p/DejxHqIpgBG/", "https://www.instagram.com/colofill/reel/DejxHqIpgBG/"]:
        assert parse_clip_url(url) == ClipKey("instagram", "DejxHqIpgBG"), url


def test_parse_other_is_none():
    assert parse_clip_url("https://www.facebook.com/watch/?v=123") is None


def test_clip_key_string():
    assert ClipKey("tiktok", "1").key == "tiktok_1"


def test_info_tiktok():
    info = clip_info_from_ytdlp(fixture("tiktok_7479505763950611758"))
    assert info.key == ClipKey("tiktok", "7479505763950611758")
    assert info.kind == "short"
    assert info.lang is None
    assert info.creator == "garyvee"


def test_info_instagram_title_from_caption():
    info = clip_info_from_ytdlp(fixture("instagram_DejxHqIpgBG"))
    assert info.key.platform == "instagram"
    assert not info.title.startswith("Video by ")
    assert info.title == "ใช้ claude ตัดต่อยังไงแบบไม่ต้องไปเรียนที่อื่น"
    assert info.duration == 0


def test_info_youtube_lang_and_kind():
    info = clip_info_from_ytdlp(fixture("youtube_3xU050kMbHM"))
    assert info.key == ClipKey("youtube", "3xU050kMbHM")
    assert info.lang == "en"
    assert info.kind == "long"
    assert info.duration == 1190


def test_info_youtube_regional_lang_normalized():
    d = fixture("youtube_3xU050kMbHM")
    d["language"] = "en-US"
    assert clip_info_from_ytdlp(d).lang == "en"


def test_ytdlp_opts_never_playlist():
    opts = YtDlpClipSource()._opts(None)
    assert opts["noplaylist"] is True
    assert "cookiesfrombrowser" not in opts
    assert YtDlpClipSource()._opts("edge")["cookiesfrombrowser"] == ("edge",)


def test_info_unsupported_extractor():
    with pytest.raises(Unavailable) as e:
        clip_info_from_ytdlp({"id": "1", "extractor_key": "Facebook", "title": "x"})
    assert e.value.reason == "unsupported"


def test_ig_login_error_classified():
    msg = "ERROR: [Instagram] x: Requested content is not available, rate-limit reached or login required"
    assert isinstance(classify_clip_error(msg, "instagram"), NeedsLogin)
    assert isinstance(classify_clip_error(msg, "youtube"), Unavailable)


@pytest.mark.network
def test_real_tiktok_and_youtube_info():
    src = YtDlpClipSource()
    for url in (TIKTOK, YOUTUBE):
        assert src.fetch_info(url).key == parse_clip_url(url)
