# ผล E2E Mini Brain Sucker (2026-11-08)

ทดสอบผ่าน `claude -p` session ใหม่ ด้วย plugin จาก worktree (`--plugin-dir`) · คลังทดสอบ `C:\brain-sucker-cache\mini\lib e2e` · `BRAINSUCK_CACHE=C:/brain-sucker-cache/mini`

## ผลแต่ละขั้น
| ขั้น | ผล |
|---|---|
| 1. `/brain-sucker:mini-brain <TikTok> <YouTube> <IG>` จากโฟลเดอร์ว่าง | ✔ ดึง + Whisper + สรุป + ลบเฟรม รวม **451 วิ** สำหรับ 3 คลิป (12 วิ + 19:50 + 57 วิ) · IG ไม่ต้องล็อกอิน · โฟลเดอร์สุ่มยังว่าง · เสนอชื่อเป็นตารางเดียว |
| 1b. ตอบ `ok` (`claude -c -p`) | ✔ ไฟล์ถูกเปลี่ยนชื่อเป็น `<key>__<slug>.md` ครบ 3 |
| 2. คุยต่อในแชทเดิม ("Kat แนะนำให้ launch กี่ครั้ง") | ✔ ตอบละเอียด ทุก bullet มี Citation `youtu.be/3xU050kMbHM?t=` · บอกตรงๆ ว่าช่วงหนึ่งใช้ข้อความบนจอเพราะถอดเสียงพลาด |
| 3. โหมดคำถามจากโฟลเดอร์ใหม่ (IG + TikTok) | ✔ Citation ชี้ URL TikTok/IG · แยกความเห็นทั่วไปออกจากที่มาจากคลิป · โฟลเดอร์ยังว่าง |
| 4. URL ซ้ำ + `--to` Advisor ทดสอบ | ✔ `existing` ใน 0.65 วิ · ไฟล์อยู่ใน `<Advisor>/clips/` · `--to` โฟลเดอร์ที่ไม่ใช่ Advisor → exit 3 |
| 4b. ถาม Advisor ทำอาหารเรื่อง silent launch | ✔ skill `advisor` อ่าน `clips/` และอ้างอิงได้ พร้อมแนะนำให้เพิ่มช่องเมื่ออยู่นอก Domain |

## สิ่งที่พบ
- **Whisper ไทยฟังชื่อเฉพาะผิด แม้มี `initial_prompt`**: "Claude" ยังเป็น "คลอส" (ทดสอบกับ prompt ว่าง vs "Claude" ได้เหมือนกัน) → summarizer แก้ชื่อจาก title/description ได้ (ชื่อที่เสนอและสรุปสะกด "Claude" ถูก)
- **Summarizer เดาเวลา Screen Text** ถ้าบอกแค่ว่า "ใช้ชื่อไฟล์" (ตรง 2/20 และมีเวลาเกินความยาวคลิป) → แก้ prompt ให้มีตัวอย่างการแปลง `t00074.jpg → [01:14]` แล้วตรง 10/10
- **เกณฑ์ ⟨ถอดไม่ชัด⟩ (`avg_logprob < -1.0`)** ไม่ติดเลยในทั้ง 3 คลิป แม้ช่วงหนึ่งของ YouTube ถอดพลาดจริง → เกณฑ์อาจหลวมไป ต้องจูนกับคลิปเสียงแย่
- **PATH ชนกับ plugin ที่ติดตั้งไว้**: `--plugin-dir` แทน skill/agent ได้ แต่ `brainsuck` บน PATH ยังเป็นของ plugin ที่ติดตั้ง (cache 0.1.0) แม้ปิด plugin ด้วย `--settings` → E2E ใช้การ prepend PATH · **หลัง merge ต้อง update/reinstall plugin `brain-sucker`** ให้เป็น 0.2.0
- ชื่อที่เสนอยาวเกิน 60 ตัวได้ (slug ตัดที่ 60 กลางคำ) — ใช้ได้ แต่ชื่อไฟล์ดูขาด
- เส้นทาง IG ล็อกอิน / NexLev ไม่ได้ทดสอบจริง (รีลทดสอบไม่ต้องล็อกอิน) — ครอบคลุมด้วย unit test เท่านั้น
