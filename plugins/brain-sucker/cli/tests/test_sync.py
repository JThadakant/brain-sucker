import pytest

from brainsuck.models import VideoRef
from brainsuck.sync import KnownVideo, SuspiciousListing, SyncPlan, plan_sync


def refs(*ids, title="t"):
    return [VideoRef(i, title, "long") for i in ids]


def known(*ids, title="t", status="active"):
    return {i: KnownVideo(i, title, status) for i in ids}


def test_new_in_remote_order():
    assert plan_sync(refs("c", "a", "b"), {}, set()).new == ["c", "a", "b"]


def test_skipped_not_new():
    assert plan_sync(refs("a", "b"), {}, {"a"}).new == ["b"]


def test_title_change_is_refresh():
    p = plan_sync([VideoRef("a", "new", "long")], known("a", title="old"), set())
    assert p == SyncPlan(new=[], refresh=["a"], removed=[], restored=[])


def test_missing_is_removed():
    assert plan_sync(refs("a", "b"), known("a", "b", "c"), set()).removed == ["c"]


def test_removed_back_is_restored():
    p = plan_sync(refs("a"), known("a", status="removed"), set())
    assert p.restored == ["a"] and p.removed == []


def test_already_removed_not_removed_again():
    p = plan_sync(refs("a"), {**known("a"), **known("z", status="removed")}, set())
    assert p.removed == []


def test_empty_listing_raises():
    with pytest.raises(SuspiciousListing):
        plan_sync([], known("a", "b", "c"), set())


def test_mass_disappearance_raises():
    ids = [f"v{i}" for i in range(20)]
    with pytest.raises(SuspiciousListing):
        plan_sync(refs(*ids[:8]), known(*ids), set())


def test_small_drop_ok():
    ids = [f"v{i}" for i in range(20)]
    assert sorted(plan_sync(refs(*ids[:18]), known(*ids), set()).removed) == ["v18", "v19"]
