"""PROTOTYPE — throwaway. Mini Brain Sucker spike: any-platform URL -> info, Whisper (auto lang), 360p frames, timings.
Usage: python p_mini.py <url> [<url>...]   (run with C:\\brain-sucker-cache\\venv python)"""
import json
import pathlib
import shutil
import sys
import time

import yt_dlp

from brainsuck.frames import extract_scene_frames
from brainsuck.transcribe import FasterWhisperTranscriber

OUT = pathlib.Path(r"C:\brain-sucker-cache\proto-mini")
OUT.mkdir(parents=True, exist_ok=True)
BASE = {"quiet": True, "no_warnings": True, "noprogress": True, "js_runtimes": {"node": {}}}
results = []
t = time.perf_counter()
whisper = FasterWhisperTranscriber()
load_s = time.perf_counter() - t
for url in sys.argv[1:]:
    r = {"url": url}
    try:
        t0 = time.perf_counter()
        with yt_dlp.YoutubeDL(BASE) as y:
            info = y.extract_info(url, download=False)
        r.update(id=info["id"], extractor=info.get("extractor_key"), title=(info.get("title") or "")[:70],
                 duration=info.get("duration"), uploader=info.get("uploader"),
                 lang=info.get("language"), info_s=round(time.perf_counter() - t0, 1))
        d = OUT / f"{info.get('extractor_key')}_{info['id']}"
        shutil.rmtree(d, ignore_errors=True)
        t0 = time.perf_counter()
        with yt_dlp.YoutubeDL({**BASE, "format": "ba[ext=m4a]/ba/b", "outtmpl": str(d / "audio.%(ext)s")}) as y:
            y.extract_info(url, download=True)
        r["audio_s"] = round(time.perf_counter() - t0, 1)
        audio = next(d.glob("audio.*"))
        t0 = time.perf_counter()
        segs, tinfo = whisper._pipe.transcribe(str(audio), batch_size=8)  # language auto-detect
        segs = list(segs)
        r.update(whisper_s=round(time.perf_counter() - t0, 1), whisper_lang=tinfo.language,
                 lang_prob=round(tinfo.language_probability, 2), text=" ".join(s.text for s in segs)[:300],
                 low_conf_segments=sum(s.avg_logprob < -1.0 for s in segs), segments=len(segs))
        t0 = time.perf_counter()
        with yt_dlp.YoutubeDL({**BASE, "format": "bv*[height<=360]/b[height<=360]/wv*/b",
                               "format_sort": ["res:360", "+size"], "outtmpl": str(d / "v360.%(ext)s")}) as y:
            y.extract_info(url, download=True)
        r["video_s"] = round(time.perf_counter() - t0, 1)
        video = next(d.glob("v360.*"))
        t0 = time.perf_counter()
        frames = extract_scene_frames(video, d / "frames", threshold=0.3, max_frames=40)
        r.update(frames=len(frames), frames_s=round(time.perf_counter() - t0, 1), frames_dir=str(d / "frames"))
    except Exception as e:  # spike: record and move on
        r["error"] = str(e)[:300]
    results.append(r)
print(json.dumps({"model_load_s": round(load_s, 1), "clips": results}, ensure_ascii=False, indent=1))
