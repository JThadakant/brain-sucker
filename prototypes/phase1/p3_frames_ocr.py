"""PROTOTYPE (c): 360p video -> ffmpeg scene detect -> dedupe -> PaddleOCR. Is on-screen text worth it?
Run with venv-ocr python. Usage: python p3_frames_ocr.py [threshold] [label...]"""
import glob
import re
import shutil
import sys
import time

from paddleocr import PaddleOCR
from PIL import Image

from common import CLIPS, OUT, YTDLP, run, url

thr = float(sys.argv[1]) if len(sys.argv) > 1 else 0.3
only = set(sys.argv[2:])
ocr = {}


def ahash(path, n=16):
    im = Image.open(path).convert("L").resize((n, n))
    px = list(im.getdata())
    avg = sum(px) / len(px)
    return [p > avg for p in px]


for vid, label, lang in CLIPS:
    if only and label not in only:
        continue
    d = OUT / label
    d.mkdir(exist_ok=True)
    vids = glob.glob(str(d / f"{vid}.v360.*"))
    if not vids:
        p, dt = run(YTDLP + ["-f", "bv*[height<=360]/b[height<=360]/wv*", "-S", "res:360,+size",
                             "-o", str(d / f"{vid}.v360.%(ext)s"), url(vid)])
        print(f"[{label}] 360p download rc={p.returncode} {dt:.1f}s")
        vids = glob.glob(str(d / f"{vid}.v360.*"))
    fdir = d / f"frames-{thr}"
    shutil.rmtree(fdir, ignore_errors=True)
    fdir.mkdir()
    p, dt_scene = run(["ffmpeg", "-hide_banner", "-i", vids[0], "-vf", f"select='gt(scene,{thr})',showinfo",
                       "-fps_mode", "vfr", str(fdir / "f%04d.jpg")])
    times = [float(m) for m in re.findall(r"pts_time:([\d.]+)", p.stderr)]
    frames = sorted(fdir.glob("*.jpg"))
    kept, last = [], None
    for f, ts in zip(frames, times):
        h = ahash(f)
        if last is None or sum(a != b for a, b in zip(h, last)) > 20:
            kept.append((f, ts))
        last = h
    key = "th" if lang == "th" else "en"
    if key not in ocr:
        ocr[key] = PaddleOCR(lang=key, ocr_version="PP-OCRv5", use_doc_orientation_classify=False,
                             use_doc_unwarping=False, use_textline_orientation=False, enable_mkldnn=False)
    t = time.perf_counter()
    lines_out = []
    for f, ts in kept:
        res = ocr[key].predict(str(f))
        texts = [tx for r in res for tx, sc in zip(r["rec_texts"], r["rec_scores"]) if sc > 0.8 and len(tx) > 2]
        if texts:
            lines_out.append(f"[{ts:7.1f}] " + " | ".join(texts))
    dt_ocr = time.perf_counter() - t
    (d / f"ocr-{thr}.txt").write_text("\n".join(lines_out), encoding="utf-8")
    print(f"\n[{label}] scene>{thr}: {len(frames)} frames ({dt_scene:.1f}s) -> {len(kept)} after dedupe "
          f"-> {len(lines_out)} with text | OCR {dt_ocr:.1f}s")
    for l in lines_out[:12]:
        print("   ", l[:200])
