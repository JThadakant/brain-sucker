"""brainsuck CLI: resolve / ingest / status. Interface: docs/DESIGN.md § ①."""
import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Callable

__version__ = "0.1.0"

EXIT_BLOCKED, EXIT_NOT_ADVISOR, EXIT_SUSPICIOUS = 2, 3, 4


def _print_json(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False), flush=True)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="brainsuck")
    p.add_argument("--version", action="version", version=f"brainsuck {__version__}")
    sub = p.add_subparsers(dest="cmd")
    r = sub.add_parser("resolve", help="find the Channel a query refers to")
    r.add_argument("query")
    i = sub.add_parser("ingest", help="ingest a Channel into an Advisor folder")
    i.add_argument("channel_id")
    i.add_argument("--advisor", required=True, type=Path)
    i.add_argument("--domain")
    i.add_argument("--screen-text", action="store_true")
    i.add_argument("--limit", type=int)
    s = sub.add_parser("status", help="what still needs summarizing / synthesizing")
    s.add_argument("advisor", type=Path)
    return p


def main(argv: list[str] | None = None, *, yt=None, make_transcriber: Callable | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code or 0)
    if args.cmd is None:
        parser.print_help()
        return 0

    if args.cmd == "status":
        from brainsuck.status import collect_status

        _print_json(collect_status(args.advisor))
        return 0

    from brainsuck.youtube import YtDlpYouTube, YouTubeError

    yt = yt or YtDlpYouTube()
    if args.cmd == "resolve":
        try:
            _print_json([asdict(c) for c in yt.resolve(args.query)])
        except YouTubeError as e:
            _print_json({"event": "error", "message": str(e)})
            return 1
        return 0

    from brainsuck.advisor import AdvisorMissing
    from brainsuck.ingest import ingest
    from brainsuck.sync import SuspiciousListing

    if make_transcriber is None:
        from brainsuck.transcribe import FasterWhisperTranscriber as make_transcriber
    cache = Path(os.environ.get("BRAINSUCK_CACHE", r"C:\brain-sucker-cache"))
    try:
        result = ingest(args.channel_id, args.advisor, yt=yt, make_transcriber=make_transcriber, cache_dir=cache,
                        domain=args.domain, screen_text=args.screen_text, limit=args.limit, emit=_print_json)
    except AdvisorMissing as e:
        _print_json({"event": "error", "kind": "not-an-advisor", "message": str(e)})
        return EXIT_NOT_ADVISOR
    except SuspiciousListing as e:
        _print_json({"event": "error", "kind": "suspicious-listing", "message": str(e)})
        return EXIT_SUSPICIOUS
    except YouTubeError as e:
        _print_json({"event": "error", "kind": "youtube", "message": str(e)})
        return 1
    return EXIT_BLOCKED if result.blocked else 0
