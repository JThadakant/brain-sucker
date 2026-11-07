# ผล Prototype Mini Brain Sucker (2026-11-08)

สคริปต์: branch `prototype/mini` → `prototypes/mini/p_mini.py` · ข้อมูลดิบ: `C:\brain-sucker-cache\proto-mini\`
เครื่องว่าง (ไม่มีงานอื่นแย่ง) · venv production `C:\brain-sucker-cache\venv`

## คลิปทดสอบ
| แพลตฟอร์ม | คลิป | ความยาว | ภาษา |
|---|---|---|---|
| TikTok | [@garyvee 7479505763950611758](https://www.tiktok.com/@garyvee/video/7479505763950611758) | 12 วิ | en |
| YouTube | [Kat Mañalac — How to Launch (YC) 3xU050kMbHM](https://www.youtube.com/watch?v=3xU050kMbHM) | 19:50 | en, มีสไลด์ |
| Instagram | [colofill DejxHqIpgBG](https://www.instagram.com/reels/DejxHqIpgBG/) (ผู้ใช้ให้มา) | สั้น | th |

## 1. TikTok — ผ่าน ไม่ต้องล็อกอิน
- `extract_info` 3.2 วิ · เสียง 1.9 วิ · Whisper 5.3 วิ · วิดีโอ 2.4 วิ · เฟรม 0.3 วิ → **รวม ~13 วิ**
- yt-dlp **list หน้าโปรไฟล์ไม่ได้** ("Unable to extract secondary user ID") — ไม่กระทบ mini (รับ URL คลิปตรง)

## 2. Instagram — ผ่าน ไม่ต้องล็อกอิน (สำหรับรีลนี้)
- `extract_info` 1.8 วิ · เสียง 22.4 วิ · Whisper 13.3 วิ (ตรวจภาษาได้ th, prob 1.0) · วิดีโอ 3.9 วิ · 5 เฟรม 2.7 วิ
- `duration` = null · `title` = "Video by <user>" (ชื่อจริงอยู่ใน description/caption) → ใช้ caption เป็นแหล่งชื่อ/ข้อมูล
- IG แยกไฟล์เสียง/ภาพ → **ต้องส่ง `ffmpeg_location` ให้ yt-dlp** (ไม่งั้นได้ format ด้อยกว่า)
- หน้าโปรไฟล์ IG แบบไม่ล็อกอิน **ไม่แสดงรีลเลย** และ yt-dlp รับ URL โปรไฟล์ไม่ได้ → เส้นทางล็อกอิน (cookies) ยังเป็น fallback ตาม design แต่ไม่ใช่ทางหลัก

## 3. สไลด์ที่ 360p — อ่านได้
- YouTube 19:50 → 40 เฟรม (scene > 0.3, cap 40) · Haiku อ่าน 8 เฟรมตัวอย่าง: **6/6 เฟรมที่มีข้อความอ่านได้ถูกต้อง** (2 เฟรมเป็นผู้พูดล้วน) รวมตัวเลขเล็ก "$33,383 pledged · 280 backers · 210%"
- สรุป: **360p พอ** ไม่ต้องขยับเป็น 480p/720p

## 4. เวลาต่อคลิป (วัดจริง)
- Whisper large-v3 ตอนเครื่องว่าง: **19:50 ใน 69 วิ = ~17× realtime** (เร็วกว่าที่วัดตอน prototype ขั้นที่ 1 ซึ่งมี OCR แย่ง CPU: 6–8×)
- โหลดโมเดล 5–13 วิ ต่อการรัน
- YouTube 20 นาที: info 2.6 + เสียง 9.0 + Whisper 69 + วิดีโอ 8.9 + เฟรม 4.1 = **~94 วิ ก่อนสรุป** (+ Haiku สรุป ~30–60 วิ) → ≈ 2–2.5 นาที
- ประมาณใหม่ (Whisper 17×): 10 นาที ≈ 1–1.5 นาที · 1 ชม. ≈ 5–6 นาที · 3 ชม. ≈ 14–16 นาที (รวมสรุป)

## ปัญหาที่พบ → ใส่ในแผน
- **Whisper ไทยฟังชื่อแบรนด์/คำอังกฤษผิด**: "Claude" → "คลอส" · YouTube อังกฤษ: ชื่อผู้พูด "Kat Mañalac" → "Ketman Yalik" · แก้: ส่ง `initial_prompt` ให้ Whisper จาก title + caption/description + ชื่อผู้สร้าง (คำเฉพาะจะสะกดถูกขึ้น) และให้ summarizer ใช้ title/description แก้ชื่อเฉพาะในสรุป
- `low_conf_segments` = 0 ทุกคลิปที่เกณฑ์ `avg_logprob < -1.0` → เกณฑ์ "ถอดไม่ชัด" ต้องจูนกับคลิปที่เสียงแย่จริง (ยังไม่มีตัวอย่าง)
