"""Advisor scaffold: the folder's CLAUDE.md and its managed list of Channels."""
import json
import re
from importlib import resources
from pathlib import Path

MARKER = "<!-- brain-sucker:advisor -->"
START = "<!-- brain-sucker:channels:start -->"
END = "<!-- brain-sucker:channels:end -->"
_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class AdvisorMissing(Exception):
    """The folder is not an Advisor yet and no Domain was given to create one."""


def _template(domain: str) -> str:
    text = resources.files("brainsuck").joinpath("templates/advisor-claude.md").read_text(encoding="utf-8")
    return text.replace("{{domain}}", domain)


def ensure_advisor(advisor_dir: Path, domain: str | None) -> None:
    path = advisor_dir / "CLAUDE.md"
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing is not None and MARKER in existing:
        return
    if not domain:
        raise AdvisorMissing(f"{advisor_dir} is not an Advisor yet; pass --domain to create one")
    advisor_dir.mkdir(parents=True, exist_ok=True)
    text = _template(domain) if existing is None else existing.rstrip("\n") + "\n\n" + _template(domain)
    path.write_text(text, encoding="utf-8", newline="\n")


def update_channel_list(advisor_dir: Path) -> None:
    lines = []
    for state_file in sorted((advisor_dir / "channels").glob("*/state.json")):
        s = json.loads(state_file.read_text(encoding="utf-8"))
        active = sum(1 for v in s["known"].values() if v["status"] == "active")
        handle = f" ({s['handle']})" if s.get("handle") else ""
        lines.append(f"- **{s['title']}**{handle} — `channels/{s['folder']}/` — {active} คลิป")
    path = advisor_dir / "CLAUDE.md"
    text = path.read_text(encoding="utf-8")
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    path.write_text(f"{head}{START}\n" + "\n".join(lines) + f"\n{END}{tail}", encoding="utf-8", newline="\n")


def channel_folder_name(handle: str | None, channel_id: str) -> str:
    name = _UNSAFE.sub("-", (handle or "").lstrip("@").lower()).strip(" .")
    return name or channel_id
