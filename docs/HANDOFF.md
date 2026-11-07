# Handoff — อ่านไฟล์นี้ก่อนเมื่อเริ่ม session ใหม่

> อัปเดตล่าสุด: 2026-11-08 · repo: `C:\Users\Lenovo\OneDrive\Desktop\brain sucker` · branch ทำงาน: `feat/v1`

## 1. Brain Sucker v1 (ระบบหลัก) — สถานะ

- เอกสาร: `docs/PLAN.md` (ภาพรวม+การตัดสินใจ), `docs/DESIGN.md`, `GLOSSARY.md`, `docs/adr/0001–0005`, `docs/research/0001–0002`
- แผน implement: `docs/superpowers/plans/2026-11-08-brain-sucker-v1.md` (12 tasks)
- **Ledger (สำคัญ)**: `.superpowers/sdd/2026-11-08-brain-sucker-v1/progress.md` — Task 1–11 `complete`, มี `Ruling:` ทุกข้อที่เบี่ยงจากแผน
- วิธีทำงานที่ผู้ใช้เลือก: **Native** (`superpowers:executing-plans`) — ทำต่อจาก ledger; ห้ามทำ task ที่ `complete` ซ้ำ
- เทส: `cd plugins/brain-sucker/cli && /c/brain-sucker-cache/venv-dev/Scripts/python -W error -m pytest -q` (81 passed) · `-m network` (3) · `-m gpu` (1)
- plugin ติดตั้งแล้ว: `brain-sucker@brain-sucker-local` (scope user, โหลดจากซอร์สตรง — แก้ไฟล์แล้ว `/reload-plugins`)
- CLI: `bash plugins/brain-sucker/bin/brainsuck {resolve|ingest|status}` (venv ที่ `C:\brain-sucker-cache\venv`)

### Task 12 (E2E) — กำลังทำ
- [x] Step 1: validate + marketplace add + install
- [~] Step 2: ingest เสร็จแล้ว (ดู done ใน log) — เหลือ summarize/synthesize · ingest Nick's Kitchen ทั้งช่อง → `C:\Users\Lenovo\OneDrive\Desktop\ที่ปรึกษาทำอาหาร` · log: `C:\brain-sucker-cache\e2e-ingest.log` (บรรทัดสุดท้าย `exit=N`) — ถ้า log ไม่มี `exit=` แปลว่าถูกตัดกลางทาง: **รันคำสั่งเดิมซ้ำได้เลย (resume)**:
  `bash plugins/brain-sucker/bin/brainsuck ingest UC2HNqPgeKtVr2gZmLeeIk3g --advisor "C:/Users/Lenovo/OneDrive/Desktop/ที่ปรึกษาทำอาหาร"`
  - ต่อจากนั้นทำตาม `plugins/brain-sucker/skills/brain-suck/SKILL.md` ข้อ 4–6: `brainsuck status` → agent `brain-sucker:video-summarizer` ทีละ 5 path (ขนาน ≤8) จน pending = 0 → `brain-sucker:channel-synthesizer` → `brain-sucker:advisor-synthesizer`
- [ ] Step 3: golden Q&A (ดูแผน Task 12) — ทดสอบจริงด้วย `claude -p "<คำถาม>"` โดย cwd = โฟลเดอร์ที่ปรึกษา · บันทึกผล `docs/research/0003-e2e.md`
- [ ] Step 4: ช่องทำอาหารภาษาไทย — **รอผู้ใช้เลือกช่อง** (≤100–150 คลิป)
- [ ] Step 5: วัดเวลา Whisper ใหม่ตอนเครื่องว่าง · final review (`superpowers:executing-plans` § Final Review: review-package + reviewer บน model ที่เก่งสุด) · `superpowers:finishing-a-development-branch`

### สิ่งที่เรียนรู้ระหว่างทำ (อย่าลืม)
- Haiku สรุปเป็น batch แล้วเอาเนื้อหาข้ามคลิปมาปน → แก้แล้ว (batch 5 + ตรวจกับ transcript ของไฟล์ตัวเอง)
- PyAV ต้อง `<16`, cuBLAS pin `12.9.2.10`, ffmpeg อยู่ใน WinGet Packages (ไม่อยู่ใน PATH)
- ห้าม shell heredoc ที่มี `'` ซับซ้อน — ใช้ Write tool เขียนไฟล์
- Test advisor สำหรับลอง agent: `C:\brain-sucker-cache\test-advisor ทดสอบ` (6 คลิป สรุป+สังเคราะห์แล้ว)

## 2. Mini Brain Sucker — ขั้นออกแบบ (brainstorming → grilling)

**ความต้องการ (คำพูดผู้ใช้):** วาง URL คลิป YouTube กี่อันก็ได้ → Claude ได้ทั้ง transcript และภาพของคลิป · ใช้บ่อยกว่าระบบหลัก · สำหรับคลิปนักธุรกิจ/คลิปให้ความรู้ที่เจอแล้วน่าสนใจ เป็นที่ปรึกษาส่วนตัว

**ตกลงแล้ว:**
- ที่เก็บ = **(b) คลังกลางเดียว** (ชื่อโฟลเดอร์ยังไม่ล็อก ชั่วคราวเรียก `mini-brain`) **และ (c) ส่งเข้าโฟลเดอร์ Advisor ของระบบหลักได้**
- ตัวอย่างการใช้ของผู้ใช้: สร้างโฟลเดอร์สุ่ม → เปิด Claude Code → รัน skill เดียว → โยน URL หลายอัน → คลิปถูกเก็บเข้าคลัง mini-brain **และ** คุยเรื่องคลิปนั้นในโฟลเดอร์สุ่มได้ทันทีโดยไม่ต้องไปเปิดที่คลัง · โฟลเดอร์ใหม่ใดๆ ก็เรียกที่ปรึกษาจากคลัง mini-brain ได้ · ตั้งชื่อให้แต่ละคลิปได้ โดย Claude เสนอชื่อให้
- ใช้ซ้ำของเดิม: YouTube seam, Whisper, frames, record codec, video-summarizer (ดูภาพได้) · คลิปธุรกิจน่าจะมีสไลด์/กราฟ → เปิดภาพเป็นค่าเริ่มต้น (ยังต้องยืนยัน)

**ขั้นถัดไป:** grilling รอบ 1 (คำถามอยู่ในแชทล่าสุด — ถ้าหาย ให้ถามใหม่จากหัวข้อ: ชื่อ/ที่ตั้งคลัง, การเรียกที่ปรึกษาจากโฟลเดอร์อื่น, ชื่อคลิป, ภาพเปิดเสมอไหม, ความเร็ว vs ความครบ, การจัดกลุ่มคลิป, การส่งเข้า Advisor (c), ซ้ำ URL) → design doc `docs/superpowers/specs/` → writing-plans

### Grill รอบ 1 — คำตอบ (2026-11-08)
- Q1 คลัง = `C:\Users\Lenovo\OneDrive\Desktop\mini-brain` (ผู้ใช้สร้างไว้แล้ว, ชื่อนี้ถาวร)
- Q2 ไม่เขียนไฟล์ลงโฟลเดอร์สุ่ม · skill เดียว: มี URL → ดึงเข้าคลัง + โหลดเนื้อหาเข้าแชท; ไม่มี URL + คำถาม → ค้นคลังแล้วตอบพร้อมอ้างอิง
- Q3 ภาพเปิดเป็นค่าเริ่มต้น (360p → scene frames → Claude ดูภาพ) · `--no-visual` ปิด
- Q4 Claude เสนอชื่อทุกคลิปเป็นตารางเดียว ผู้ใช้ ok/แก้ · เก็บชื่อจริงไว้ด้วย
- Q5 โฟลเดอร์เดียว + `index.md` + แท็กอัตโนมัติ
- Q6 URL ซ้ำ → ใช้ของเดิม (`--refresh` เพื่อดึงใหม่)
- Q7 `--to "<Advisor>"` → copy เข้า `<Advisor>/clips/` (แยกจาก channels/) + แก้ skill advisor ให้อ่าน clips/
- Q8 **รับ YouTube + Instagram + TikTok** (เปลี่ยนจากคำแนะนำ) → เปิดคำถามเรื่อง IG/TikTok login, ภาษา (Whisper auto-detect)
- Q9 ยังไม่ทำ synthesis ระดับคลัง
