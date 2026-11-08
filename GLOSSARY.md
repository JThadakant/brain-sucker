# Brain Sucker

เครื่องมือที่ดูดเนื้อหาทั้งหมดของช่อง YouTube มาเป็นความรู้ แล้วทำให้โฟลเดอร์หนึ่งกลายเป็นที่ปรึกษาในหัวข้อนั้น

## ที่ปรึกษาและช่อง

**Advisor**:
โฟลเดอร์หนึ่งโฟลเดอร์ที่ทำหน้าที่เป็นที่ปรึกษาในหนึ่ง Domain โดยตอบจากความรู้ของ Channel ทุกช่องที่อยู่ในโฟลเดอร์นั้น
_Avoid_: bot, assistant, workspace, project

**Domain**:
หัวข้อที่ Advisor ให้คำปรึกษา เช่น "ทำอาหาร" กำหนดตอนสร้าง Advisor
_Avoid_: niche, category, topic (ใช้ Topic สำหรับความหมายอื่น)

**Channel**:
ช่อง YouTube หนึ่งช่องที่ถูก Ingest เข้า Advisor ระบุตัวตนด้วย channel ID ไม่ใช่ handle หรือชื่อช่อง
_Avoid_: creator, source, account

**Channel Query**:
สิ่งที่ผู้ใช้พิมพ์เพื่อระบุ Channel ซึ่งอาจเป็น @handle, URL หรือชื่อช่องเป็นข้อความธรรมดา ต้อง resolve ให้ได้ Channel เดียวก่อนเริ่ม Ingest
_Avoid_: channel name (ชื่อช่องเป็นแค่รูปแบบหนึ่งของ Channel Query)

## วิดีโอและเนื้อหา

**Video**:
คลิปหนึ่งคลิปของ Channel มี Kind เป็น Long หรือ Short เท่านั้น
_Avoid_: episode, post (ใช้ Clip สำหรับ Video ที่ผู้ใช้ส่ง URL มาเอง)

**Clip**:
Video ที่ผู้ใช้ส่ง URL มาเองผ่าน mini-brain ไม่ได้มาจากการ Ingest ทั้ง Channel มาจาก YouTube, Instagram หรือ TikTok
_Avoid_: post, reel

**Clip Library**:
โฟลเดอร์กลางเดียวที่เก็บ Video Record ของทุก Clip (`Desktop\mini-brain`) เรียกใช้ได้จากทุกโฟลเดอร์
_Avoid_: vault, inbox

**Clip Key**:
`<platform>_<id>` ตัวตนของ Clip
_Avoid_: URL (URL หลายแบบชี้ Clip เดียวกันได้)

**Display Name**:
ชื่อที่ผู้ใช้ตั้งให้ Clip (Claude เสนอ) ใช้เป็นชื่อไฟล์และชื่อใน Citation โดยยังเก็บ title จริงไว้
_Avoid_: nickname, label

**Long / Short**:
ประเภทของ Video: Long คือคลิปปกติ ส่วน Short คือ YouTube Shorts ไลฟ์ไม่นับเป็น Video ในระบบนี้
_Avoid_: full video, reel

**Transcript**:
ข้อความคำพูดในวิดีโอพร้อม timestamp ได้มาจากซับของ YouTube หรือจากการถอดเสียงเอง
_Avoid_: subtitle, caption (สองคำนี้ใช้ได้เฉพาะเมื่อพูดถึงแหล่งที่มาของ Transcript)

**On-screen Text**:
ข้อความที่ปรากฏบนภาพในวิดีโอ เช่น สไลด์ สูตร หรือรายการวัตถุดิบ พร้อม timestamp
_Avoid_: OCR result, frame text, visual content

**Video Record**:
ไฟล์ความรู้ของ Video หนึ่งคลิป รวม metadata, Transcript, On-screen Text และ Video Summary ไว้ด้วยกัน
_Avoid_: video file, note, doc

**Removed Video**:
Video ที่เคย Ingest แล้ว แต่ภายหลังถูกลบหรือถูกตั้งเป็นส่วนตัวบน YouTube ยังเก็บ Video Record ไว้และยังใช้เป็นความรู้ได้ แต่ Citation จะบอกว่าคลิปนี้ไม่อยู่บน YouTube แล้ว
_Avoid_: deleted video, dead link

**Skipped Video**:
Video ที่ Ingest ไม่ได้และถูกบันทึกเหตุผลไว้ เช่น เฉพาะสมาชิก จำกัดอายุ หรือไม่มีเสียงพูด
_Avoid_: failed video, error

## การดูดและความรู้

**Ingest**:
กระบวนการเปลี่ยน Channel ให้กลายเป็น Channel Knowledge ภายใน Advisor ครั้งแรกจะดึงทุก Video ครั้งต่อไปจะดึงเฉพาะ Video ใหม่
_Avoid_: scrape, crawl, import, sync, download

**Channel Knowledge**:
ความรู้ทั้งหมดของ Channel หนึ่งช่องใน Advisor ประกอบด้วย Video Record, Topic Map, Principles, Evolution และ Channel Glossary
_Avoid_: knowledge base (กว้างเกินไป), database, index

**Video Summary**:
สรุปใจความของ Video หนึ่งคลิป เป็นส่วนหนึ่งของ Video Record
_Avoid_: digest, notes

**Topic Map**:
แผนที่ที่บอกว่าแต่ละ Topic ถูกพูดถึงใน Video ไหนบ้าง
_Avoid_: tags, categories

**Topic**:
เรื่องย่อยที่ Channel พูดถึง เช่น "การพักเนื้อ" หรือ "ซอสฝรั่งเศส" อยู่ภายใต้ Domain
_Avoid_: subject, theme

**Principles**:
หลักการ framework และวิธีคิดที่ Channel ใช้ซ้ำ ๆ ข้ามหลาย Video
_Avoid_: rules, tips, playbook

**Evolution**:
บันทึกว่าความเห็นของ Channel ในเรื่องหนึ่งเปลี่ยนไปอย่างไรตามเวลา
_Avoid_: changelog, history

**Channel Glossary**:
ศัพท์เฉพาะที่ Channel หนึ่งใช้ เป็นคนละอย่างกับไฟล์ GLOSSARY.md นี้
_Avoid_: dictionary, terms

**Advisor Synthesis**:
ความรู้ระดับ Advisor ที่สังเคราะห์ข้าม Channel ได้แก่ Topic รวม จุดที่ทุกช่องเห็นตรงกัน จุดที่เห็นต่าง และช่องไหนเด่นเรื่องอะไร
_Avoid_: summary, overview, consensus

## การตอบคำถาม

**Citation**:
การอ้างอิง Video พร้อม timestamp ที่ใช้เป็นหลักฐานประกอบคำตอบ
_Avoid_: source, reference, link

**Provenance Label**:
ป้ายที่ติดไว้กับแต่ละส่วนของคำตอบ มี 3 แบบเท่านั้น คือ **From Channel** (มาจากช่อง), **Inferred** (อนุมานจาก Principles ของช่อง) และ **General Knowledge** (ความรู้ทั่วไป ไม่ได้มาจากช่อง)
_Avoid_: confidence, tag

**Recency Weighting**:
กฎที่ให้ Video ใหม่มีน้ำหนักมากกว่า Video เก่า**ภายใน Channel เดียวกัน** ไม่ใช้ตัดสินระหว่าง Channel
_Avoid_: freshness, time decay

**Channel Focus**:
การจำกัดให้ Advisor ตอบจาก Channel ที่ผู้ใช้ระบุเท่านั้น
_Avoid_: filter, mode
