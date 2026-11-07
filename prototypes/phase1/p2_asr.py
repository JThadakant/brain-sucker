"""PROTOTYPE (b): YouTube subs vs faster-whisper large-v3 on RTX 4070.
Run with venv-asr python. Usage: python p2_asr.py [model] [label...]"""
import glob
import json
import os
import pathlib
import sys
import time

import nvidia.cublas  # noqa: E402  (pinned 12.9.2.10 wheel; add DLL dir before ctranslate2 loads)

for d in nvidia.cublas.__path__:
    b = pathlib.Path(d) / "bin"
    if b.exists():
        os.add_dll_directory(str(b))
        os.environ["PATH"] = str(b) + os.pathsep + os.environ["PATH"]

from faster_whisper import BatchedInferencePipeline, WhisperModel  # noqa: E402

from common import CLIPS, OUT, YTDLP, run, url  # noqa: E402

model_name = sys.argv[1] if len(sys.argv) > 1 else "large-v3"
only = set(sys.argv[2:])

t = time.perf_counter()
model = WhisperModel(model_name, device="cuda", compute_type="float16")
pipe = BatchedInferencePipeline(model=model)
print(f"[load {model_name}] {time.perf_counter() - t:.1f}s")


def subs_text(d):
    f = next(iter(sorted(d.glob("*.json3"))), None)
    if not f:
        return None, None
    ev = json.loads(f.read_text(encoding="utf-8")).get("events", [])
    txt = " ".join("".join(s.get("utf8", "") for s in e.get("segs", [])) for e in ev if e.get("segs"))
    return f.name, " ".join(txt.split())


def cer(a, b):
    a, b = a.replace(" ", ""), b.replace(" ", "")
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1] / max(len(a), 1)


for vid, label, lang in CLIPS:
    if only and label not in only:
        continue
    d = OUT / label
    d.mkdir(exist_ok=True)
    audio = glob.glob(str(d / f"{vid}.audio.*"))
    if not audio:
        p, dt = run(YTDLP + ["-f", "ba[ext=m4a]/ba", "-o", str(d / f"{vid}.audio.%(ext)s"), url(vid)])
        print(f"[{label}] audio download rc={p.returncode} {dt:.1f}s")
        audio = glob.glob(str(d / f"{vid}.audio.*"))
    t = time.perf_counter()
    segs, info = pipe.transcribe(audio[0], language=lang, batch_size=8)
    segs = list(segs)
    dt = time.perf_counter() - t
    w_txt = " ".join(" ".join(s.text for s in segs).split())
    (d / f"whisper-{model_name}.txt").write_text(
        "\n".join(f"[{s.start:7.1f}] {s.text.strip()}" for s in segs), encoding="utf-8")
    print(f"\n[{label}] {model_name}: {info.duration:.0f}s audio in {dt:.1f}s "
          f"(x{info.duration / dt:.0f} realtime) | {len(segs)} segments")
    name, s_txt = subs_text(d)
    if s_txt:
        sample = slice(0, 600) if lang == "th" else slice(0, 400)
        print(f"   CER whisper vs {name}: {cer(s_txt[:4000], w_txt[:4000]):.2%}")
        print(f"   SUBS   : {s_txt[sample]}")
    else:
        print("   (no YouTube subs to compare)")
    print(f"   WHISPER: {w_txt[:600 if lang == 'th' else 400]}")
