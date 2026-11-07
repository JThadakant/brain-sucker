"""Decide what an incremental Ingest must do, from the remote listing and what we already know."""
from dataclasses import dataclass
from typing import Literal

from brainsuck.models import VideoRef


@dataclass(frozen=True)
class KnownVideo:
    id: str
    title: str
    status: Literal["active", "removed"]


@dataclass(frozen=True)
class SyncPlan:
    new: list[str]
    refresh: list[str]
    removed: list[str]
    restored: list[str]


class SuspiciousListing(Exception):
    """The listing looks broken (empty or most videos gone); refusing to mark videos removed."""


def plan_sync(remote: list[VideoRef], known: dict[str, KnownVideo], skipped: set[str]) -> SyncPlan:
    remote_ids = {r.id for r in remote}
    active = [k for k in known.values() if k.status == "active"]
    gone = [k.id for k in active if k.id not in remote_ids]
    if active and not remote:
        raise SuspiciousListing(f"listing is empty but {len(active)} videos are known")
    if len(gone) > 5 and len(gone) > len(active) / 2:
        raise SuspiciousListing(f"{len(gone)} of {len(active)} known videos disappeared")
    return SyncPlan(
        new=[r.id for r in remote if r.id not in known and r.id not in skipped],
        refresh=[r.id for r in remote if r.id in known and known[r.id].title != r.title],
        removed=gone,
        restored=[r.id for r in remote if r.id in known and known[r.id].status == "removed"],
    )
