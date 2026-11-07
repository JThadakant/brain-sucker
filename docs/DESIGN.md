# Brain Sucker — Module Design

> ขั้นที่ 2 · ใช้ศัพท์จาก `GLOSSARY.md` (domain) และ codebase-design (Module / Interface / Seam / Adapter / Depth)

## ภาพรวม: 2 ซีก แยกกันที่ระบบไฟล์

```
/brain-sucker:brain-suck  (skill — ผู้ควบคุม)
   │
   ├─①  brainsuck CLI (Python, deterministic)  ── เขียน ──▶  Video Records + index.md + state.json
   │
   ├─②  video-summarizer agents (Haiku)          ── เติม ──▶  ## Summary ใน Video Record
   │
   └─③  synthesizer agents (Opus)                ── เขียน ──▶  topics / principles / evolution / glossary / advisor.md

เปิด Claude ในโฟลเดอร์ Advisor ── CLAUDE.md ──▶ skill `advisor` (กฎการตอบ) ──▶ อ่าน Channel Knowledge
```

**Seam หลักคือรูปแบบไฟล์** (Video Record + `state.json`) — ซีก Python ไม่รู้จัก LLM, ซีก Claude ไม่รู้จัก yt-dlp/Whisper. แต่ละซีกทดสอบได้ด้วยไฟล์ตัวอย่าง

## ① `brainsuck` CLI — Module ลึกตัวเดียว, Interface 3 คำสั่ง

| คำสั่ง | Interface (สิ่งที่ผู้เรียกต้องรู้) |
|---|---|
| `brainsuck resolve <channel-query>` | คืน JSON: รายการ Channel ที่เป็นไปได้ (id, title, handle, subscribers, video count) · @handle/URL → 1 รายการ, ข้อความ → สูงสุด 3 |
| `brainsuck ingest <channel-id> --advisor <dir> [--domain <text>] [--screen-text] [--limit N]` | สร้าง Advisor ถ้ายังไม่มี (ต้องมี `--domain`) · Ingest แบบ incremental, resume ได้, idempotent · stdout = JSON lines ความคืบหน้า · exit 0 แม้มี Skipped Video (บันทึกใน `skipped.md`) · exit ≠ 0 เฉพาะเมื่อ YouTube บล็อกทั้งหมด |
| `brainsuck status <advisor-dir>` | คืน JSON: ต่อ Channel — จำนวน Video, จำนวนที่ `summary: pending`, รายการ path ที่รอสรุป, ต้อง synthesize ใหม่ไหม |

ทุกอย่างอื่นซ่อนอยู่ข้างใน:

### Internal seams (ใช้ในเทสของ CLI เอง ไม่โผล่ที่ Interface)

| ส่วนภายใน | ประเภท dependency | Adapters |
|---|---|---|
| **YouTube** — `list_channel`, `fetch_video` (info + captions), `fetch_audio`, `fetch_video_360p` | true external | `YtDlpYouTube` (จริง) · `FixtureYouTube` (อ่านจาก `tests/fixtures/`) → **seam จริง 2 adapters** |
| **Transcriber** — `transcribe(audio, lang) → segments` | external heavy (GPU) | `FasterWhisper` · `FakeTranscriber` → **seam จริง** |
| **Sync planner** — `(remote listing, state) → actions[new / metadata-changed / removed / unchanged]` | in-process (pure) | ไม่มี seam — ทดสอบตรง |
| **Transcript policy** — `(lang, captions available) → source` (en: manual > en-orig · th: whisper) | in-process (pure) | ทดสอบตรง |
| **Record codec** — `render(record) → markdown`, `parse(markdown) → record` (รักษา `## Summary` เดิมเมื่ออัปเดต metadata) | in-process | ทดสอบตรง (round-trip) |
| **State store** — `state.json` | local-substitutable (tmp dir) | ใช้ไฟล์จริงใน tmp |
| **Index writer** — `index.md` (ใหม่→เก่า, Long ก่อน Short ใน view) | in-process + fs | tmp dir |

Screen Text (`--screen-text`): CLI ทำแค่ ffmpeg scene detect → บันทึกเฟรมไว้ที่ cache + list ใน record (`screen_frames:`) · การ "ดูภาพ" เป็นงานของ summarizer agent ไม่ใช่ CLI

## รูปแบบ Video Record (`channels/<handle>/videos/<YYYY-MM-DD>_<id>.md`)

```markdown
---
id: K_SXQoMdSf4
channel_id: UC2HNqPgeKtVr2gZmLeeIk3g
title: How France Perfected Beef Stew
kind: long            # long | short
published: 2026-10-01
duration: 368
url: https://www.youtube.com/watch?v=K_SXQoMdSf4
lang: en
transcript_source: youtube-manual   # youtube-manual | youtube-auto | whisper-large-v3
status: active        # active | removed
summary: pending      # pending | done
screen_frames: []     # path ใน cache เมื่อเปิด --screen-text
---
## Summary
(pending)

## Description
...

## Transcript
[00:00] This is the best recipe on earth for ...
[00:31] ...
```

- Transcript ใช้ timestamp `[mm:ss]` ต้นบรรทัด → Citation สร้างลิงก์ `?t=` ได้ทันที
- Summarizer แก้เฉพาะ `## Summary` + ตั้ง `summary: done` (+ `topics:` ใน front-matter)

## ② `video-summarizer` agent (Haiku)
- Interface: รับรายการ path ของ Video Record (batch ~10) → เขียน `## Summary` (ใจความ, ขั้นตอน/สูตร, คำแนะนำสำคัญพร้อม timestamp, topics) แล้วตั้ง `summary: done`
- ถ้ามี `screen_frames` → ดูภาพแล้วเพิ่ม `## Screen Text`

## ③ Synthesizer agents (Opus)
- `channel-synthesizer`: อ่าน `index.md` + ทุก `## Summary` ของ Channel → เขียน `topics.md`, `principles.md`, `evolution.md`, `glossary.md` (incremental: รับรายการ Video ใหม่ + ไฟล์เดิม)
- `advisor-synthesizer`: อ่านไฟล์สังเคราะห์ของทุก Channel → เขียน `advisor.md` (Advisor Synthesis)

## Advisor runtime — กฎการตอบอยู่ใน plugin ไม่ใช่ใน CLAUDE.md
- `CLAUDE.md` ของ Advisor สั้น: Domain + รายชื่อ Channel + "โหลด skill `brain-sucker:advisor` ก่อนตอบทุกครั้ง"
- กฎทั้งหมด (Citation, Recency Weighting, Provenance Label, Channel Focus, การเทียบข้ามช่อง) อยู่ใน skill `advisor` ของ plugin → **แก้กฎครั้งเดียว ทุก Advisor ได้กฎใหม่** (locality) แทนที่จะต้องไล่แก้ CLAUDE.md ทุกโฟลเดอร์

## โครงสร้าง repo

```
brain sucker/                       ← marketplace
├── .claude-plugin/marketplace.json
├── docs/ GLOSSARY.md prototypes/
└── plugins/brain-sucker/
    ├── .claude-plugin/plugin.json
    ├── skills/
    │   ├── brain-suck/SKILL.md     ← ผู้ควบคุม ①②③
    │   └── advisor/SKILL.md        ← กฎการตอบ
    ├── agents/
    │   ├── video-summarizer.md     (model: haiku)
    │   ├── channel-synthesizer.md  (model: opus)
    │   └── advisor-synthesizer.md  (model: opus)
    ├── templates/advisor-claude.md ← กลายเป็น CLAUDE.md ของ Advisor
    └── cli/                        ← Python package `brainsuck` + tests
        ├── pyproject.toml
        ├── src/brainsuck/
        └── tests/
```
venv อยู่ที่ `${CLAUDE_PLUGIN_DATA}/venv` · skill `brain-suck` สร้างให้ครั้งแรก (pin `av<16`, `nvidia-cublas-cu12==12.9.2.10`)

## ยังเปิดอยู่ (ไม่อยู่ใน v1)
- NexLev fallback รายคลิปเมื่อ yt-dlp ถูกบล็อก → v1 บันทึกเป็น Skipped Video เหตุผล `blocked` ให้รันซ้ำทีหลัง
- full-text index ถ้า grep ไม่ทัน (ADR 0001)
