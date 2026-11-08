import glob

import pytest

AUDIO = glob.glob(r"C:\brain-sucker-cache\proto\out\nick-short-chives\*.audio.m4a")
IG_AUDIO = glob.glob(r"C:\brain-sucker-cache\proto-mini\Instagram_*\audio.*")


@pytest.mark.gpu
@pytest.mark.skipif(not AUDIO, reason="prototype audio not in cache")
def test_whisper_short_clip():
    from pathlib import Path

    from brainsuck.transcribe import FasterWhisperTranscriber

    segs = FasterWhisperTranscriber().transcribe(Path(AUDIO[0]), "en")
    assert segs and "chives" in " ".join(s.text for s in segs).lower()
    assert segs[0].start < 5


@pytest.mark.gpu
@pytest.mark.skipif(not IG_AUDIO, reason="mini prototype audio not in cache")
def test_whisper_clip_detects_thai():
    from pathlib import Path

    from brainsuck.transcribe import FasterWhisperTranscriber

    segs, lang = FasterWhisperTranscriber().transcribe_clip(Path(IG_AUDIO[0]), None, "Claude")
    assert lang == "th"
    assert segs
