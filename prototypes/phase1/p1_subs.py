"""PROTOTYPE (a): Can yt-dlp list the channel and fetch subs without PO token / cookies?
Run with venv-asr python."""
import json
from common import CLIPS, OUT, YTDLP, run, url

UC = "UC2HNqPgeKtVr2gZmLeeIk3g"

for tab in ("videos", "shorts"):
    p, dt = run(YTDLP + ["--flat-playlist", "-J", "--extractor-args", "youtubetab:approximate_date",
                         f"https://www.youtube.com/channel/{UC}/{tab}"])
    entries = json.loads(p.stdout)["entries"] if p.returncode == 0 else []
    dates = [e.get("timestamp") or e.get("upload_date") for e in entries]
    print(f"[list {tab}] {len(entries)} entries in {dt:.1f}s | has dates: {sum(1 for d in dates if d)}/{len(entries)}")
    warns = [l for l in p.stderr.splitlines() if "WARNING" in l or "ERROR" in l]
    for w in warns[:5]:
        print("   ", w)

for vid, label, lang in CLIPS:
    d = OUT / label
    d.mkdir(exist_ok=True)
    langs = f"{lang},{lang}-orig"
    p, dt = run(YTDLP + ["--skip-download", "--write-info-json", "--write-subs", "--write-auto-subs",
                         "--sub-langs", langs, "--sub-format", "json3", "-t", "sleep",
                         "-o", str(d / "%(id)s.%(ext)s"), url(vid)])
    info = json.loads((d / f"{vid}.info.json").read_text(encoding="utf-8")) if (d / f"{vid}.info.json").exists() else {}
    manual = sorted(info.get("subtitles", {}).keys())
    auto_orig = [k for k in info.get("automatic_captions", {}) if k.endswith("-orig") or k == lang]
    got = sorted(f.name for f in d.glob("*.json3"))
    print(f"\n[{label}] rc={p.returncode} {dt:.1f}s | manual subs: {manual or '-'} | auto(orig): {auto_orig or '-'}")
    print(f"   downloaded: {got or 'NONE'}")
    for w in [l for l in p.stderr.splitlines() if "WARNING" in l or "ERROR" in l][:6]:
        print("   ", w[:220])
