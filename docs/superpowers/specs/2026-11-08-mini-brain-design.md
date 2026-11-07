# Mini Brain Sucker — Design

> 2026-11-08 · ออกแบบผ่าน brainstorming + grilling 3 รอบ (คำตอบดิบ: `docs/HANDOFF.md` §2) · ศัพท์: `GLOSSARY.md`

## เจตนา

ระบบหลัก (Brain Sucker) ดูดทั้งช่องเป็นชั่วโมงถึงทั้งวัน เหมาะกับการสร้าง "สมอง" ของช่องหนึ่ง แต่ใช้ไม่บ่อย ผู้ใช้อยากได้ทางที่เร็วและใช้บ่อยกว่า: **เจอคลิปน่าสนใจ (โดยเฉพาะนักธุรกิจ/คลิปให้ความรู้) → โยน URL ให้ Claude → Claude ได้ทั้งคำพูดและภาพของคลิป → คุยต่อได้ทันที และคลิปถูกเก็บสะสมเป็นที่ปรึกษาส่วนตัว**

ตัวอย่างการใช้ของผู้ใช้: เจอคลิปสอน "ให้ Claude ตัดต่อวิดีโอแบบเทพ" → สร้างโฟลเดอร์สุ่ม เปิด Claude Code → `/mini-brain <url> <url>` → คุยเรื่องคลิปในโฟลเดอร์นั้นได้เลย และคลิปถูกเก็บเข้าคลัง → วันหลังเปิดโฟลเดอร์ไหนก็ได้ `/mini-brain <คำถาม>` → ตอบจากคลังพร้อมอ้างอิง

## เป้าหมาย / ไม่ใช่เป้าหมาย / ล้มเหลวถ้า

- **เป้าหมาย:** URL หลายอันในคำสั่งเดียว · YouTube (รวม Shorts) + Instagram + TikTok · ได้ transcript + ภาพ · คุยได้ทันทีในโฟลเดอร์ปัจจุบัน · คลังกลางสะสม เรียกได้จากทุกโฟลเดอร์ · Claude เสนอชื่อคลิป · ส่งคลิปเข้า Advisor ของระบบหลักได้
- **ไม่ใช่เป้าหมาย (v1):** ไฟล์สังเคราะห์ระดับคลัง (advisor.md) · โฟลเดอร์ย่อย/หมวด · แพลตฟอร์มอื่น (Facebook ฯลฯ)
- **ล้มเหลวถ้า:** เขียนไฟล์รกลงโฟลเดอร์สุ่มของผู้ใช้ · ช้าจนไม่อยากใช้ (เป้า: ไม่กี่นาทีต่อคลิป) · ถามรหัสผ่าน/ข้อมูลบัญชี · ตอบจาก transcript ที่ถอดผิดโดยไม่บอก

## วิธีที่พิจารณา

| วิธี | ข้อดี | ข้อเสีย | ผล |
|---|---|---|---|
| **A. skill ตัวที่สองใน plugin `brain-sucker` + คำสั่ง `brainsuck clip`** ใช้ package เดิม | ใช้ seam YouTube/Whisper/frames/record/summarizer ซ้ำ · แก้บั๊กที่เดียวได้ทั้งสองระบบ · รูปแบบไฟล์เดียวกัน → `--to` ง่าย | plugin ใหญ่ขึ้น | **เลือก** |
| B. plugin แยก | อิสระ | โค้ดซ้ำ/ติดตั้งสองชุด | ตัด |
| C. ใช้ NexLev/vidIQ "ดูคลิปแล้วตอบ" อย่างเดียว | ไม่ต้องสร้างอะไร | เสียเครดิตทุกคลิป · ไม่มี transcript ดิบ · ไม่สะสมในเครื่อง | ใช้เป็น fallback ของ IG เท่านั้น |

## สิ่งที่ผู้ใช้ตัดสินแล้ว

1. **คลัง** = `C:\Users\Lenovo\OneDrive\Desktop\mini-brain` (มีอยู่แล้ว) — ตั้ง path ไว้ใน config จุดเดียว
2. **ไม่เขียนไฟล์ลงโฟลเดอร์ปัจจุบัน** · skill เดียว `mini-brain` (พิมพ์ `/mini-brain`, ชื่อเต็ม `/brain-sucker:mini-brain`):
   - มี URL → ดึงเข้าคลัง แล้วอ่าน record เข้าแชทนั้น → คุยต่อได้ทันที
   - ไม่มี URL + คำถาม → ค้นคลัง ตอบพร้อม Citation (กฎเดียวกับ skill `advisor`)
3. **ภาพเปิดเป็นค่าเริ่มต้น**: 360p → ffmpeg scene frames → summarizer (Haiku) ดูภาพ เขียน `## Screen Text` · `--no-visual` ปิด
4. **ชื่อคลิป**: หลังสรุป Claude เสนอชื่อทุกคลิปเป็นตารางเดียว ผู้ใช้ตอบ ok หรือแก้รายคลิป · ชื่อนี้ = ชื่อไฟล์ + ชื่อที่ใช้อ้างอิงในแชท · เก็บ `title` จริงไว้ด้วย
5. **คลังเรียบ**: ทุก record ในโฟลเดอร์ `clips/` ของคลัง + `index.md` + แท็กอัตโนมัติ (ใช้ `topics:` ของ summarizer)
6. **URL ซ้ำ** → ใช้ record เดิม (`--refresh` ดึงใหม่) · ระบุตัวตนด้วย platform + video id ไม่ใช่ URL ดิบ
7. **ส่งเข้า Advisor**: `--to "<Advisor>"` → เก็บในคลังตามปกติ + copy record ไป `<Advisor>/clips/` · skill `advisor` ต้องค้น `clips/` ด้วย · ไม่แตะ `channels/`
8. **แพลตฟอร์ม**: YouTube + Instagram + TikTok
9. **Transcript**:
   - mini: **Whisper large-v3 ทุกคลิป** (ทุกแพลตฟอร์ม ทุกภาษา) · IG/TikTok ใช้ language auto-detect ของ Whisper · YouTube ใช้ภาษาจาก info ถ้ามี
   - ระบบหลัก (เพิ่มเข้า v1.1): quality gate ตอนดึง (คำ/นาทีต่ำผิดปกติ, ส่วนใหญ่เป็น `[music]`, ภาษาไม่ตรง → Whisper) + summarizer ตั้ง `transcript_quality: poor` → `brainsuck ingest` รอบถัดไปถอดใหม่ด้วย Whisper
   - ตอนตอบ: ถ้าอ้างช่วงที่ถอดความไม่ชัด ต้องบอกตรงๆ
10. **IG บังคับล็อกอิน**: Claude ถามผู้ใช้ "ใช้การล็อกอิน IG ที่มีอยู่ใน browser ไหม (ใช่ / ไม่ / ใช่ทุกครั้ง)" — **ไม่ถามรหัสผ่าน/อีเมลใดๆ** · ใช่ → `cookies_from_browser` (ลอง Edge/Firefox ก่อน Chrome เพราะ Chrome บน Windows เข้ารหัส cookie) · "ใช่ทุกครั้ง" จำไว้ใน config ของคลัง · ไม่ / อ่าน cookie ไม่ได้ → NexLev `watch_instagram_video_and_ask` (ได้คำบรรยายแทน transcript, ติด `transcript_source: nexlev-description`) · ไม่ได้อีก → ข้ามพร้อมเหตุผล
11. **ไม่ทำ synthesis ระดับคลังใน v1**

## โครงสร้าง (ตัดสินโดยผู้ออกแบบ — แก้ได้)

```
Desktop\mini-brain\
├── config.json          ← {"ig_cookies": "ask" | "always" | "never", "browser": "edge"}
├── index.md             ← ตาราง: ชื่อที่ตั้ง | แพลตฟอร์ม | ผู้สร้าง | วันที่ | แท็ก | ไฟล์
└── clips\<platform>_<id>__<slug ชื่อที่ตั้ง>.md   ← Video Record (รูปแบบเดียวกับระบบหลัก)
```
- Video Record เพิ่ม field: `platform: youtube|instagram|tiktok`, `display_name:`, `creator:`, `transcript_quality:` · kind ของ IG/TikTok = `short`
- CLI: `brainsuck clip <url...> --library <dir> [--no-visual] [--refresh] [--to <advisor>]` → JSON lines เหมือน ingest · `brainsuck clip-name <library> <id> "<ชื่อ>"` (ตั้งชื่อ + rename ไฟล์ + อัปเดต index) · `brainsuck clip-search <library> <คำ>` ไม่จำเป็น (ใช้ grep)
- YouTube seam ขยายเป็นรับ URL ทั่วไปของ yt-dlp (`fetch_info(url)`) — adapter เดิมยังใช้ได้
- ลำดับใน skill: `brainsuck clip` → summarizer (batch ≤5, ดูภาพ) → เสนอชื่อ (ตาราง) → `brainsuck clip-name` → อ่าน record ทั้งหมดเข้าแชท → พร้อมคุย

## การตัดสินของผู้ออกแบบหลัง builder check (ผู้ใช้ตรวจได้)
- **`--to` copy เมื่อไร:** copy หลังขั้นตั้งชื่อ (`brainsuck clip-name` เป็นคนทำ) จึงได้ record ที่สรุปแล้วและมีชื่อ · `--refresh`/เปลี่ยนชื่อ → อัปเดต copy ใน `<Advisor>/clips/` ด้วย (คลังเก็บว่า copy ไปไหนบ้าง) · v1: `advisor.md`, `status`, รายชื่อใน CLAUDE.md **ไม่นับ** clips — มีแค่ skill `advisor` ที่ค้น `clips/`
- **ถอดไม่ชัดรายบรรทัด:** เก็บ `avg_logprob` ของแต่ละ segment จาก Whisper · บรรทัดที่ต่ำกว่าเกณฑ์ต่อท้าย ` ⟨ถอดไม่ชัด⟩` (หัวบรรทัด `[mm:ss]` เหมือนเดิม จึงไม่กระทบ record เก่า) · `transcript_quality` ระดับคลิป = สัดส่วนบรรทัดที่ไม่ชัด
- **NexLev fallback:** Claude เรียก MCP แล้วส่งข้อความให้ `brainsuck clip-import` สร้าง record (ชื่อไฟล์/index สม่ำเสมอ) · ถามผู้ใช้ครั้งเดียวต่อชุดก่อนใช้เครดิต ("ใช้เครดิต NexLev กับ N คลิปไหม")
- **ถาม IG ล็อกอินเมื่อไร:** หลังลองแบบไม่ล็อกอินแล้วล้มเท่านั้น · CLI ส่ง event `{"event":"needs-login","id":…}` · skill ถามผู้ใช้ แล้วรันซ้ำด้วย `--ig-cookies <browser>`

## ปล่อยให้ผู้สร้างตัดสิน
- รูปแบบ slug ชื่อไฟล์ (ไทยได้ ตัดอักขระต้องห้ามของ Windows)
- จำนวนเฟรมสูงสุดต่อคลิป (เริ่ม 40 เหมือนระบบหลัก)
- เกณฑ์ตัวเลขของ quality gate (ตั้งจากการลองกับคลิปจริง)

## ต้องพิสูจน์ใน prototype ก่อนวางแผนละเอียด
1. yt-dlp ดึง TikTok สาธารณะได้โดยไม่ล็อกอินไหม
2. yt-dlp ดึง IG reel ได้ไหม (ไม่ล็อกอิน / cookies จาก Edge / Firefox / Chrome)
3. Haiku อ่านสไลด์จากเฟรม 360p ได้ชัดพอไหม (ถ้าไม่ → 480p/720p)
4. เวลาจริงต่อคลิป (Whisper + เฟรม + สรุป) บนเครื่องนี้
