# Brain Sucker — แผนโปรเจกต์

> สรุปจาก grilling session วันที่ 2026-11-08 · ใช้เองส่วนตัว

## เป้าหมาย

ใส่ชื่อช่อง YouTube → ดึงเนื้อหาทั้งหมดในช่อง → สร้าง knowledge base → โฟลเดอร์นั้นกลายเป็น "ที่ปรึกษา" ในหัวข้อนั้น

## Design ที่ตกลงแล้ว

### รูปแบบ
- **Claude Code plugin** ติดตั้งระดับ user (ใช้ได้ทุกโฟลเดอร์) · คำสั่งเดียว `/brain-suck <ช่อง>`
- **1 โฟลเดอร์ = 1 ที่ปรึกษา (1 domain)** · มีได้หลายช่อง
- รัน `/brain-suck` ในโฟลเดอร์ที่ยังไม่เป็นที่ปรึกษา → ถาม "ที่ปรึกษาด้านอะไร" แล้วสร้าง `CLAUDE.md` · ในโฟลเดอร์ที่เป็นแล้ว → เพิ่มช่องใหม่ / อัปเดตช่องเดิม
- เปิด Claude ในโฟลเดอร์ = คุยกับที่ปรึกษาทันที (ไม่มีคำสั่ง `/advisor`)
- โฟลเดอร์ `brain sucker` นี้ = **ซอร์สโค้ดของ plugin**

### โครงสร้างโฟลเดอร์ที่ปรึกษา
```
<โฟลเดอร์ที่ปรึกษา>/
├── CLAUDE.md          ← บทบาทที่ปรึกษา + กฎการตอบ
├── advisor.md         ← สังเคราะห์ข้ามช่อง: หัวข้อรวม, จุดเห็นตรงกัน/เห็นต่าง, ช่องไหนเด่นเรื่องอะไร
└── channels/<handle>/
    ├── index.md       ← ตารางคลิปทั้งหมด ใหม่→เก่า
    ├── topics.md      ← แผนที่หัวข้อ → คลิป
    ├── principles.md  ← หลักการ / framework / วิธีคิด
    ├── evolution.md   ← ความเห็นที่เปลี่ยนไปตามเวลา
    ├── glossary.md    ← ศัพท์เฉพาะของช่อง
    ├── skipped.md     ← คลิปที่ดึงไม่ได้ + เหตุผล
    ├── state.json     ← คลิปที่ประมวลผลแล้ว (สำหรับ incremental sync)
    └── videos/<date>_<id>.md  ← metadata + transcript + ข้อความบนจอ + สรุป
```
ไฟล์หนัก (วิดีโอ เสียง เฟรม) อยู่ที่ `C:\brain-sucker-cache\` (นอก OneDrive, ตั้งค่าได้) และลบหลังประมวลผล

### ดึงข้อมูล
| เรื่อง | ตัดสินใจ |
|---|---|
| ขอบเขต | transcript + metadata + Shorts + ข้อความบนจอ · **ไม่เอา** live, comments |
| แหล่งหลัก | `yt-dlp` (มี delay, resume ได้) · fallback NexLev MCP รายคลิป |
| Transcript | อังกฤษ: ซับ YouTube (`en` > `en-orig`) · ไทย: `faster-whisper large-v3` ทุกคลิป (ซับไทยอัตโนมัติผิดเยอะ) · ไม่ใช้ turbo |
| ภาพ | **ปิดเป็นค่าเริ่มต้น** · เปิดรายช่องด้วย `--screen-text`: 360p → ffmpeg scene detection (เฉพาะเปลี่ยนฉากใหญ่) → Claude ดูภาพ (ไม่ใช้ OCR) → ลบวิดีโอ |
| ภาษา | ไทย + อังกฤษ |
| ขนาด | ออกแบบรองรับหลักพันคลิป · ใช้ไฟล์ markdown + index, ไม่ใช้ vector DB |
| อัปเดต | incremental — ดึงเฉพาะคลิปใหม่ |
| ข้าม | members-only, age-restricted, ไม่มีเสียงพูด → `skipped.md` |
| ตัวตนช่อง | อ้างอิงด้วย channel ID ใน `state.json` · ชื่อโฟลเดอร์ `channels/<handle>/` คงไว้ตามตอน Ingest ครั้งแรกแม้ handle จะเปลี่ยน |
| ช่องซ้ำหลาย Advisor | แต่ละ Advisor Ingest แยกกัน ไม่แชร์ข้อมูล |
| คลิปถูกลบ/ซ่อนภายหลัง | เก็บ Video Record ไว้ ติดสถานะ `removed` · Citation แจ้งว่าไม่อยู่บน YouTube แล้ว |
| คลิปเก่าถูกแก้ชื่อ/คำอธิบาย | Ingest ครั้งถัดไปอัปเดตเฉพาะ metadata ไม่ถอดเสียงหรือสรุปใหม่ |

### สร้าง knowledge base
- สรุปรายคลิป: **Haiku subagents** ใน Claude Code (ใช้โควตาแพ็กเกจ)
- สังเคราะห์ (principles/topics/evolution/advisor.md): **Opus**
- Fallback ถ้าโควตาไม่พอ: Claude Batch API

### กฎการตอบของที่ปรึกษา
1. อ้างอิงคลิป + timestamp (ลิงก์ `?t=`) ทุกครั้ง
2. **ภายในช่องเดียวกัน** คลิปใหม่มีน้ำหนักมากกว่า · ถ้าเปลี่ยนความเห็น บอกว่า "เคยแนะนำ X (ปี) แต่เปลี่ยนแล้วใน [คลิป]"
3. คลิปยาว > Shorts
4. หลายช่องเห็นต่าง → แสดงมุมมองแต่ละช่องเทียบกัน + จุดเห็นตรงกัน → ค่อยแนะนำ (ติดป้ายชัด) · ไม่รวมเป็นเสียงเดียว · recency ไม่ใช้ตัดสินข้ามช่อง
5. ติดป้ายแยก: **จากช่อง** / **อนุมานจากหลักการของช่อง** / **ความรู้ทั่วไป**
6. ตอบภาษาเดียวกับที่ถาม · ยกประโยคต้นฉบับเป็นหลักฐาน
7. ค่าเริ่มต้นตอบจากทุกช่อง · "@handle" หรือ "ถาม X อย่างเดียว" เพื่อจำกัด

### ช่องทดสอบ
1. **Nick's Kitchen** — `UC2HNqPgeKtVr2gZmLeeIk3g` (อังกฤษ, 87 คลิปยาว + 102 Shorts) — ไม่ใช่ Nick DiGiovanni
2. ช่องทำอาหารภาษาไทย 1 ช่อง (เลือกตอนขั้นที่ 6) → ทดสอบไทย + หลายช่อง

### สภาพแวดล้อม (ตรวจ 2026-11-08)
Windows 11 · Python 3.12.10 · Node 24.15 · yt-dlp 2026.10.26 · RTX 4070 Laptop 8GB · RAM 32GB · **ยังไม่มี ffmpeg** (ติดตั้งผ่าน winget ในขั้นที่ 1)

## แผนทีละขั้น + Skills

### ขั้นที่ 0 — บันทึก Design
- [ ] `mattpocock-skills:domain-modeling` → `GLOSSARY.md` + ADRs (`docs/adr/`)
- [ ] `mattpocock-skills:research` → ยืนยัน: yt-dlp limits/PO token, PaddleOCR ภาษาไทย, Thonburian vs large-v3, โครงสร้าง Claude Code plugin (agent `claude-code-guide`)

### ปรับตามผล research (docs/research/0001-tech-facts.md)
- yt-dlp ต้องมี JS runtime + `yt-dlp-ejs` → `pip install -U "yt-dlp[default,curl-cffi]"` + `--js-runtimes node` · ห้าม `--sub-langs all` (ซับแปลอัตโนมัติโดน 429) · ~300 คลิป/ชม. ไม่ใช้ cookies → resume เป็นข้อบังคับ
- Whisper ภาษาไทย: ห้ามใช้ turbo · Thonburian ไม่มี CT2 ทางการ (ต้อง convert เอง) และไม่เน้น timestamp → ทดสอบใน prototype · Windows ต้องการแค่ cuBLAS CUDA 12 (ไม่ต้อง cuDNN แล้ว)
- PaddleOCR ไทย = PP-OCRv5 mobile เท่านั้น (pin `ocr_version="PP-OCRv5"`) · เริ่มบน CPU · venv แยกจาก Whisper · Tesseract `tha` เป็น baseline เทียบ
- Plugin: โฟลเดอร์นี้เป็น **marketplace** · ตัว plugin อยู่ `plugins/brain-sucker/` · คำสั่งเต็มคือ `/brain-sucker:brain-suck` · template CLAUDE.md ของ Advisor ต้องใช้ชื่ออื่นในซอร์ส · venv อยู่ใน `${CLAUDE_PLUGIN_DATA}`

### ขั้นที่ 1 — Prototype ส่วนเสี่ยง
- [x] ติดตั้ง ffmpeg 9.0.2 (winget)
- [x] `mattpocock-skills:prototype` · อัปเกรด yt-dlp + ejs, faster-whisper (CUDA/cuBLAS), PaddleOCR (CPU)
- [x] 3 คลิป Nick's Kitchen + 1 คลิปไทย → ผล: `docs/research/0002-phase1-prototype.md`
- [ ] อ่าน plugin **watch-video** (Anthropic Directory) เป็นตัวอย่าง

### ขั้นที่ 2 — สถาปัตยกรรม + แผน implement
- [x] `mattpocock-skills:codebase-design` → `docs/DESIGN.md`
- [x] `superpowers:writing-plans` → `docs/superpowers/plans/2026-11-08-brain-sucker-v1.md` (12 tasks)

### ขั้นที่ 3 — Ingest pipeline (Python)
- [ ] `mattpocock-skills:tdd` สำหรับ logic ล้วน (resolver parsing, state, markdown writer, recency weighting)
- [ ] `superpowers:subagent-driven-development` ทำตามแผน
- [ ] `mattpocock-skills:diagnosing-bugs` เมื่อ yt-dlp/Whisper พัง

### ขั้นที่ 4 — Knowledge layer
- [ ] `mattpocock-skills:writing-for-agents` → prompt สำหรับ Haiku (รายคลิป) และ Opus (สังเคราะห์)
- [ ] skill `claude-api` เฉพาะถ้าต้อง fallback ไป Batch API

### ขั้นที่ 5 — แพ็กเป็น plugin
- [ ] `superpowers:writing-skills` → `/brain-suck` skill + template `CLAUDE.md`
- [ ] `anthropic-skills:skill-creator` → eval การ trigger
- [ ] agent `claude-code-guide` → manifest + local marketplace install

### ขั้นที่ 6 — E2E
- [ ] โฟลเดอร์ "ที่ปรึกษาทำอาหาร" ← Nick's Kitchen → + ช่องไทย
- [ ] golden Q&A set: timestamp, recency, cross-channel, การติดป้าย · `superpowers:verification-before-completion`
- [ ] `superpowers:requesting-code-review`

## Skills ในตลาดที่สำรวจแล้ว
| ตัวที่เจอ | สถานะ |
|---|---|
| watch-video (Anthropic Directory) | อ่านเป็นตัวอย่างในขั้นที่ 1 |
| baoyu-youtube-transcript (skills.sh, 22.3K installs) | อ่านเป็นตัวอย่างวิธีดึงซับ |
| Local Whisper / TubeAlfred / Arcmira | ไม่ใช้ — ซ้ำกับสิ่งที่มีอยู่ |

ไม่มีตัวไหนทำงานระดับทั้งช่อง → เขียน pipeline เอง
