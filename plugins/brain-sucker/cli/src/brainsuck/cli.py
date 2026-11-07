"""brainsuck CLI: resolve / ingest / status (docs/DESIGN.md § ①) and clip / clip-name / clip-import / clip-status
(docs/superpowers/specs/2026-11-08-mini-brain-design.md)."""
import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Callable

__version__ = "0.2.0"

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
    c = sub.add_parser("clip", help="add video URLs (YouTube / TikTok / Instagram) to the Clip Library")
    c.add_argument("urls", nargs="+")
    c.add_argument("--no-visual", action="store_true")
    c.add_argument("--refresh", action="store_true")
    c.add_argument("--to", action="append", type=Path, default=[])
    c.add_argument("--ig-cookies", choices=["auto", "edge", "firefox", "chrome"])
    c.add_argument("--remember", action="store_true")
    n = sub.add_parser("clip-name", help="set a Clip's Display Name")
    n.add_argument("key")
    n.add_argument("name")
    m = sub.add_parser("clip-import", help="make a Clip from a description text file (NexLev fallback)")
    m.add_argument("--url", required=True)
    m.add_argument("--text-file", required=True, type=Path)
    m.add_argument("--title", default="")
    m.add_argument("--creator", default="")
    m.add_argument("--to", action="append", type=Path, default=[])
    t = sub.add_parser("clip-status", help="Clip Library path, config, pending and unnamed Clips")
    for q in (c, n, m, t):
        q.add_argument("--library", type=Path)
    return p


def _clip_main(args, clip_source, make_transcriber: Callable | None) -> int:
    from dataclasses import replace

    from brainsuck.advisor import MARKER
    from brainsuck.clip import clip, import_text
    from brainsuck.clipsource import parse_clip_url
    from brainsuck.library import DEFAULT_LIBRARY, ClipLibrary, library_status, slugify

    lib = ClipLibrary(args.library or Path(os.environ.get("BRAINSUCK_LIBRARY") or DEFAULT_LIBRARY))
    lib.root.mkdir(parents=True, exist_ok=True)
    if args.cmd == "clip-status":
        _print_json(library_status(lib))
        return 0
    if args.cmd == "clip-name":
        r = lib.read(args.key)
        if r is None:
            _print_json({"event": "error", "kind": "unknown-clip", "key": args.key})
            return 1
        if not slugify(args.name):
            _print_json({"event": "error", "kind": "bad-name", "name": args.name})
            return 1
        path = lib.write(replace(r, display_name=args.name.strip()))
        _print_json({"event": "named", "key": args.key, "path": str(path)})
        return 0

    for advisor in args.to:
        claude_md = advisor / "CLAUDE.md"
        if not (claude_md.exists() and MARKER in claude_md.read_text(encoding="utf-8")):
            _print_json({"event": "error", "kind": "not-an-advisor", "path": str(advisor)})
            return EXIT_NOT_ADVISOR
    if args.cmd == "clip-import":
        key = parse_clip_url(args.url)
        if key is None:
            _print_json({"event": "error", "kind": "bad-url", "url": args.url})
            return 1
        path = import_text(lib, url=args.url, text=args.text_file.read_text(encoding="utf-8"), title=args.title,
                           creator=args.creator, to=args.to)
        _print_json({"event": "clip", "key": key.key, "path": str(path), "status": "new"})
        return 0

    if clip_source is None:
        from brainsuck.clipsource import YtDlpClipSource

        clip_source = YtDlpClipSource()
    if make_transcriber is None:
        from brainsuck.transcribe import FasterWhisperTranscriber as make_transcriber
    cache = Path(os.environ.get("BRAINSUCK_CACHE", r"C:\brain-sucker-cache"))
    result = clip(args.urls, lib, source=clip_source, make_transcriber=make_transcriber, cache_dir=cache,
                  visual=not args.no_visual, refresh=args.refresh, ig_cookies=args.ig_cookies,
                  remember=args.remember, to=args.to, emit=_print_json)
    return EXIT_BLOCKED if result.blocked else 0


def main(argv: list[str] | None = None, *, yt=None, make_transcriber: Callable | None = None,
         clip_source=None) -> int:
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

    if args.cmd.startswith("clip"):
        return _clip_main(args, clip_source, make_transcriber)

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
