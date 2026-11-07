from datetime import date

import pytest

from brainsuck.models import VideoRecord


@pytest.fixture
def make_record():
    def _make(**kw) -> VideoRecord:
        base = dict(
            id="K_SXQoMdSf4", channel_id="UC2HNqPgeKtVr2gZmLeeIk3g", title="Beef Stew", kind="long",
            published=date(2026, 10, 1), duration=368, url="https://www.youtube.com/watch?v=K_SXQoMdSf4",
            lang="en", transcript_source="youtube-auto", status="active", summary_status="pending",
            topics=[], screen_frames=[], summary_md="(pending)", description="d",
            transcript_lines=["[00:00] hello"],
        )
        base.update(kw)
        return VideoRecord(**base)
    return _make
