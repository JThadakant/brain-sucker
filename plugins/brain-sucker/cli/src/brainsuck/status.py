"""What the brain-suck skill still has to do in an Advisor: Video Records awaiting a summary, stale syntheses."""
from pathlib import Path

import yaml

from brainsuck.record import record_filename
from brainsuck.store import ChannelStore


def _covers(topics: Path) -> int:
    if not topics.exists():
        return 0
    parts = topics.read_text(encoding="utf-8").split("---\n", 2)
    front = yaml.safe_load(parts[1]) if len(parts) == 3 else None
    return int((front or {}).get("covers") or 0)


def collect_status(advisor_dir: Path) -> dict:
    channels = []
    for state_file in sorted((advisor_dir / "channels").glob("*/state.json")):
        store = ChannelStore(state_file.parent)
        state = store.load_state()
        records = list(store.iter_records())
        done = sum(r.summary_status == "done" for r in records)
        channels.append({
            "folder": state.folder,
            "channel_id": state.channel_id,
            "title": state.title,
            "videos": len(records),
            "skipped": len(state.skipped),
            "pending": [str((store.videos_dir / record_filename(r)).resolve())
                        for r in records if r.summary_status == "pending"],
            "needs_synthesis": done != _covers(state_file.parent / "topics.md"),
        })
    return {"advisor": str(advisor_dir.resolve()), "channels": channels}
