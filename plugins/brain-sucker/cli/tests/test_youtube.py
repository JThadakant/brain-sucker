import pathlib
from datetime import date

import pytest

from brainsuck.youtube import Blocked, Unavailable, YtDlpYouTube, classify_error
from fakes import FixtureYouTube

FIX = pathlib.Path(__file__).parent / "fixtures" / "youtube"


@pytest.fixture
def yt():
    return FixtureYouTube(FIX)


def test_fixture_lists_long_then_short(yt):
    channel, refs = yt.list_channel("UC2HNqPgeKtVr2gZmLeeIk3g")
    assert channel.handle == "@NicksKitchen"
    assert [r.kind for r in refs] == ["long"] * 4 + ["short"]
    assert refs[-1].id == "wrZZf2ER3ak"


def test_fixture_info_maps_fields(yt):
    yt.list_channel("UC2HNqPgeKtVr2gZmLeeIk3g")
    info = yt.fetch_info("K_SXQoMdSf4")
    assert info.duration == 368
    assert info.kind == "long"
    assert info.published == date(2026, 10, 30)
    assert info.lang == "en"
    assert info.captions["en"] == "manual"
    assert info.captions["en-orig"] == "auto"
    assert "th" not in info.captions or info.captions["th"] == "manual"


def test_fixture_short_kind_from_listing(yt):
    yt.list_channel("UC2HNqPgeKtVr2gZmLeeIk3g")
    assert yt.fetch_info("wrZZf2ER3ak").kind == "short"


def test_fixture_thai_lang(yt):
    assert yt.fetch_info("LexQiGdPlxU").lang == "th"


def test_fixture_members_only_unavailable(yt):
    with pytest.raises(Unavailable) as e:
        yt.fetch_info("MEMBERS0001")
    assert e.value.reason == "members-only"


def test_fixture_captions(yt):
    segs = yt.fetch_captions("cM5IAypOOfM", "en-orig")
    assert len(segs) > 5 and "chocolate" in " ".join(s.text for s in segs)


def test_fixture_blocked_after(yt):
    yt = FixtureYouTube(FIX, blocked_after=1)
    yt.fetch_info("K_SXQoMdSf4")
    with pytest.raises(Blocked):
        yt.fetch_info("cM5IAypOOfM")


@pytest.mark.parametrize("msg, kind, reason", [
    ("ERROR: [youtube] x: Sign in to confirm you’re not a bot. Use --cookies", Blocked, None),
    ("ERROR: HTTP Error 429: Too Many Requests", Blocked, None),
    ("ERROR: [youtube] x: Join this channel to get access to members-only content", Unavailable, "members-only"),
    ("ERROR: [youtube] x: Sign in to confirm your age. This video may be inappropriate", Unavailable, "age-restricted"),
    ("ERROR: [youtube] x: Private video. Sign in if you've been granted access", Unavailable, "private"),
    ("ERROR: [youtube] x: Video unavailable. This video has been removed", Unavailable, "unavailable"),
])
def test_classify_error(msg, kind, reason):
    err = classify_error(msg)
    assert isinstance(err, kind)
    if reason:
        assert err.reason == reason


@pytest.mark.network
def test_ytdlp_list_nicks_kitchen():
    channel, refs = YtDlpYouTube().list_channel("UC2HNqPgeKtVr2gZmLeeIk3g")
    assert channel.channel_id == "UC2HNqPgeKtVr2gZmLeeIk3g"
    assert sum(r.kind == "long" for r in refs) >= 80
    assert sum(r.kind == "short" for r in refs) >= 90


@pytest.mark.network
def test_ytdlp_resolve_handle_and_text():
    yt = YtDlpYouTube()
    assert yt.resolve("Nick's Kitchen")[0].channel_id == "UC2HNqPgeKtVr2gZmLeeIk3g"
    handle = yt.resolve("Nick's Kitchen")[0].handle
    assert [c.channel_id for c in yt.resolve(handle)] == ["UC2HNqPgeKtVr2gZmLeeIk3g"]


@pytest.mark.network
def test_ytdlp_captions_k_sxq():
    yt = YtDlpYouTube()
    info = yt.fetch_info("K_SXQoMdSf4")
    assert info.captions.get("en") == "manual"
    assert len(yt.fetch_captions("K_SXQoMdSf4", "en")) > 20
