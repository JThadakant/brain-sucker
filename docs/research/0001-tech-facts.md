# 0001 — ข้อเท็จจริงทางเทคนิค (yt-dlp, Whisper ไทย, OCR ไทย, Claude Code plugin)

> ค้นคว้าวันที่ 2026-11-08 · อ้างอิงเฉพาะแหล่งปฐมภูมิ (docs ทางการ, GitHub README/wiki/issues/source, Hugging Face model card, paper ต้นฉบับ, docs ของ Anthropic)
> สิ่งที่ยืนยันจากแหล่งปฐมภูมิไม่ได้จะอยู่ในหัวข้อ "Unconfirmed / open" ของแต่ละข้อ
> ข้อความที่ขึ้นต้นด้วย **[ข้อเสนอ]** เป็นข้อสรุปหรือคำแนะนำของผู้ค้นคว้า ไม่ได้มาจากเอกสารโดยตรง

## เวอร์ชันและวันที่ของสิ่งที่อ่าน

| แหล่ง | เวอร์ชัน / วันที่ |
|---|---|
| yt-dlp | release `2026.10.26` (เผยแพร่ 2026-10-26) · README บน master · pyproject ของ tag 2026.10.26 pin `yt-dlp-ejs==0.8.0` |
| yt-dlp wiki: PO Token Guide | แก้ไขล่าสุด 2026-07-12 |
| yt-dlp wiki: EJS, Extractors, FAQ | อ่านฉบับปัจจุบัน 2026-11-08 (ไม่มีวันที่แก้ไขในไฟล์ raw) |
| yt-dlp known-issues #3766 | อัปเดตล่าสุด 2026-08-27 |
| faster-whisper | `1.2.1` (2025-10-31) · README บน master |
| CTranslate2 | `4.8.5` (2026-11-02) · CHANGELOG + build script บน master (commit ล่าสุด 2026-11-07) |
| Thonburian Whisper | GitHub README + model card `biodatlab/whisper-th-large-v3-combined` (2024-02-20) + paper ICNLSP 2024 |
| OpenAI Whisper turbo | GitHub discussion #2363 (2024-10-01) |
| PaddleOCR | `3.7.0` (2026-06-11) · paddlepaddle บน PyPI `3.3.1` |
| EasyOCR | `1.7.2` (2024-09-24) |
| Tesseract | upstream `5.5.4` (2026-10-28) · UB Mannheim Windows build `v5.4.0.20240606` |
| ffmpeg | `ffmpeg-filters.html`, `ffmpeg.html` ฉบับปัจจุบัน 2026-11-08 |
| Claude Code docs | code.claude.com อ่าน 2026-11-08 · Claude Code บนเครื่องนี้ `2.1.318` |

สภาพเครื่องที่ตรวจระหว่างค้นคว้า (ไม่ได้ติดตั้งอะไร): yt-dlp `2026.10.26` ติดตั้งผ่าน pip ที่ `...\Python312\Scripts\yt-dlp.exe` · **ไม่มี** แพ็กเกจ `yt-dlp-ejs` · **ไม่มี** `deno` · driver NVIDIA `591.86` (nvidia-smi รายงาน CUDA 13.1) · VRAM 8188 MiB

---

## 1. yt-dlp — ดึงทั้งช่อง (/videos + /shorts) และซับหลักร้อยถึงหลักพันคลิป

### Findings

**JavaScript runtime / EJS (บังคับแล้ว)**
- yt-dlp ต้องใช้ JavaScript runtime ภายนอกเพื่อแก้ JS challenge ของ YouTube โดยรัน script จากโปรเจกต์ `yt-dlp-ejs` — https://github.com/yt-dlp/yt-dlp/wiki/EJS
- runtime ที่รองรับ: Deno (แนะนำ, เปิดเป็นค่าเริ่มต้น, ขั้นต่ำ `2.3.0`), Node (ขั้นต่ำ `22.0.0`, ต้องเปิดด้วย `--js-runtimes node`), QuickJS/QuickJS-NG, Bun (deprecated, รองรับถึง `1.3.14`) — https://github.com/yt-dlp/yt-dlp/wiki/EJS
- ถ้าติดตั้ง yt-dlp ผ่าน pip ต้องติดตั้ง script ด้วย `pip install -U "yt-dlp[default]"` (กลุ่ม `default` มี `yt-dlp-ejs`) หรือใช้ `--remote-components ejs:github` หรือ `ejs:npm` (ตัวหลังใช้ได้กับ Deno/Bun เท่านั้น) · ตัว `.exe` ทางการมี EJS ฝังมาแล้ว — https://github.com/yt-dlp/yt-dlp/wiki/EJS
- tag `2026.10.26` pin `yt-dlp-ejs==0.8.0` ในกลุ่ม `default` — https://github.com/yt-dlp/yt-dlp/blob/2026.10.26/pyproject.toml
- ลำดับความสำคัญ runtime: deno > node > quickjs > bun และ "Only "deno" is enabled by default" — https://github.com/yt-dlp/yt-dlp#general-options (README, option `--js-runtimes`)
- ถ้าไม่มี runtime จะมีคำเตือนว่าการดึง YouTube แบบไม่มี JS runtime "has been deprecated, and some formats may be missing" (เห็นใน log ของ issue) — https://github.com/yt-dlp/yt-dlp/issues/17904
- release `2026.06.09` ยกขั้นต่ำ Deno เป็น v2.3.0, Node v22 ขึ้นไป — https://github.com/yt-dlp/yt-dlp/releases/tag/2026.06.09
- release `2026.10.26` ยกขั้นต่ำ Python เป็น 3.11 — https://github.com/yt-dlp/yt-dlp/releases/tag/2026.10.26

**Player clients และ PO Token**
- client เริ่มต้นคือ `tv_samsung,visionos,web` · ถ้าไม่มี JS runtime จะตัด `web` กับ `tv_samsung` ออก · ถ้าส่ง cookies ที่ล็อกอินแล้ว จะใช้ `web_embedded,tv_samsung,web` (บัญชีฟรี) — https://github.com/yt-dlp/yt-dlp#youtube (README, extractor-arg `player_client`)
- PO Token อาจจำเป็นใน 3 กรณี: GVS (สตรีมวิดีโอ), Player request และ **Subs (คำขอซับไตเติล)** · ตารางปัจจุบัน: `web` ต้องใช้กับ Subs+GVS · `mweb` ต้องใช้กับ GVS · `tv`, `web_embedded`, `android_vr` ไม่ต้องใช้ — https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide
- ไม่แนะนำให้ดึง PO Token เองแล้ว เพราะ token ผูกกับ video ID · แนะนำ plugin `bgutil-ytdlp-pot-provider` (ดูแลโดย maintainer ของ yt-dlp) หรือ `yt-dlp-getpot-wpc` — https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide
- ค่าเริ่มต้นของ yt-dlp จะเลือก client ที่ยังไม่ต้องใช้ PO Token · ถ้ามีปัญหาให้ใช้ `mweb` + PO Token — https://github.com/yt-dlp/yt-dlp/wiki/Extractors

**Rate limit, 429 และ bot check**
- rate limit ด้วยค่าเริ่มต้น: guest ประมาณ 300 วิดีโอ/ชม. (~1000 webpage/player requests/ชม.) · บัญชีประมาณ 2000 วิดีโอ/ชม. (~4000 requests/ชม.) · แนะนำหน่วง 5–10 วินาทีระหว่างดาวน์โหลดด้วย `-t sleep` — https://github.com/yt-dlp/yt-dlp/wiki/Extractors
- `-t sleep` เท่ากับ `--sleep-subtitles 5 --sleep-requests 0.75 --sleep-interval 10 --max-sleep-interval 20` — https://github.com/yt-dlp/yt-dlp#preset-aliases
- ความหมาย: `--sleep-requests` หน่วงระหว่าง request ตอนดึงข้อมูล · `--sleep-interval` หน่วงก่อนดาวน์โหลดแต่ละไฟล์ · `--sleep-subtitles` หน่วงก่อนดาวน์โหลดซับแต่ละไฟล์ — https://github.com/yt-dlp/yt-dlp#workarounds
- HTTP 429 ตอนโหลดซับ (issue #13831): maintainer ยืนยันว่า **ซับที่คนทำ (manual) และ auto-caption ภาษาต้นฉบับไม่โดน 429** มีแค่ auto-caption ที่ **แปลอัตโนมัติ** เป็นภาษาอื่นที่โดน · ถ้าต้องการซับแปลอัตโนมัติ ให้รอประมาณ 60 วินาที (`--sleep-subtitles 60`) หรือส่ง cookies สดจากเบราว์เซอร์ — https://github.com/yt-dlp/yt-dlp/issues/13831#issuecomment-3712613129
- `youtube:skip=translated_subs` ตัดแค่ **manual subs ที่แปล** ไม่ได้ตัด auto-caption ที่แปล — https://github.com/yt-dlp/yt-dlp/issues/13831 (คอมเมนต์ของ bashonly วันที่ 2026-01-18)
- รายงานเดือน ส.ค. 2026: ผู้ใช้ยังเจอ 429 ตอนโหลดซับ และ contributor แนะนำให้ใช้ cookies หรือ `--sleep-subtitles` สูง (>70) — https://github.com/yt-dlp/yt-dlp/issues/17536 (ปิดเป็น duplicate ของ #13831)
- "Sign in to confirm you're not a bot" อยู่ในรายการ intractable issue: แปลว่า IP ถูก YouTube บล็อกตอนไม่ได้ล็อกอิน · ส่ง cookies ได้ แต่บัญชีเสี่ยงโดนบล็อก · ทางที่ปลอดภัยกว่าคือเปลี่ยน IP · PO Token provider ช่วยป้องกันได้ แต่ช่วยไม่ได้ถ้าโดนบล็อกไปแล้ว — https://github.com/yt-dlp/yt-dlp/issues/3766 (อ้าง #10128)
- `This content isn't available, try again later` = เกิน rate limit — https://github.com/yt-dlp/yt-dlp/wiki/Extractors
- FAQ: 429/402 = บริการบล็อก IP เพราะใช้งานหนักเกิน · มักเป็น soft block แก้ได้ด้วยการแก้ CAPTCHA ในเบราว์เซอร์แล้วส่ง cookies — https://github.com/yt-dlp/yt-dlp/wiki/FAQ#http-error-429-too-many-requests-or-402-payment-required

**Cookies**
- การใช้บัญชีกับ yt-dlp "you run the risk of it being banned (temporarily or permanently)" · แนะนำให้ใช้เมื่อจำเป็น หรือใช้บัญชีทิ้ง · cookies จำเป็นแค่กับเนื้อหาที่ต้องล็อกอิน (private, age-restricted, members-only) — https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies
- วิธี export ที่ไม่ถูก rotate: เปิดหน้าต่าง incognito → ล็อกอิน → ไป `https://www.youtube.com/robots.txt` → export cookies → ปิดหน้าต่าง · **ห้าม** ใช้ `--cookies-from-browser` export — https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies
- งานดาวน์โหลดยาวทั้งเพลย์ลิสต์มักล้มเพราะ cookies หมดอายุกลางทาง (issue ยังเปิดอยู่, มี PR #17891) — https://github.com/yt-dlp/yt-dlp/issues/17837

**Option สำหรับ list ช่อง/ซับ/ไม่โหลดวิดีโอ**
- `--flat-playlist` = ไม่ extract entry ทีละตัว · metadata บางส่วนอาจหายไป — https://github.com/yt-dlp/yt-dlp#general-options
- `youtubetab:approximate_date` = ดึง `upload_date` แบบประมาณใน flat-playlist — https://github.com/yt-dlp/yt-dlp#youtubetab-youtube-playlists-channels-feeds-etc
- URL ของช่องดาวน์โหลดทุก upload · ถ้าต้องการเฉพาะแท็บ ให้ส่ง URL ของแท็บนั้น (เช่น `/videos`, `/shorts`) — https://github.com/yt-dlp/yt-dlp#differences-in-default-behavior
- `--skip-download` (alias `--no-download`) ยังเขียนไฟล์ที่เกี่ยวข้อง (ซับ, info-json) — https://github.com/yt-dlp/yt-dlp#filesystem-options
- `--write-subs`, `--write-auto-subs`, `--sub-langs` (รองรับ regex และใช้ `-` เพื่อตัดออก), `--sub-format`, `--list-subs` — https://github.com/yt-dlp/yt-dlp#subtitle-options
- `--download-archive FILE` ข้ามวิดีโอที่มีในไฟล์ archive แล้ว · `--break-on-existing` หยุดเมื่อเจอวิดีโอที่อยู่ใน archive — https://github.com/yt-dlp/yt-dlp#video-selection
- `-i/--ignore-errors` · maintainer แนะนำให้ใส่ `-i` เพื่อให้ซับที่ล้มไม่ทำให้ทั้งงานล้ม และใส่ `-t sleep` เมื่อโหลดหลายวิดีโอ — https://github.com/yt-dlp/yt-dlp/issues/13831 (คอมเมนต์ bashonly 2025-07-24)
- `curl_cffi` เป็น dependency ที่แนะนำ (ใช้ impersonate) — https://github.com/yt-dlp/yt-dlp#dependencies

**ดาวน์โหลดเฉพาะ 360p**
- ตัวอย่างใน README: `-f "bv*[height<=480]+ba/b[height<=480] / wv*+ba/w"` · `-S "res:480"` = เลือกความละเอียดสูงสุดที่ไม่เกิน 480 · `-S +size,+br,+res,+fps` ดีกว่า `-f worst` — https://github.com/yt-dlp/yt-dlp#format-selection-examples และ https://github.com/yt-dlp/yt-dlp#sorting-formats
- `wv`/`bv` = video-only (ไม่มีเสียง) · filter `[height<=?720]` ใส่ `?` เพื่อรวม format ที่ไม่รู้ความสูง — https://github.com/yt-dlp/yt-dlp#format-selection
- format 18 คือ 360p (มีรายงานว่าบางกรณีเหลือแค่ format นี้) — https://github.com/yt-dlp/yt-dlp/issues/17542

### Implications for Brain Sucker

1. **ต้องแก้ environment ก่อนทำ prototype** (PLAN ยังไม่ได้ตรวจเรื่องนี้): ตอนนี้ yt-dlp จาก pip ไม่มี `yt-dlp-ejs` และไม่มี deno ทำให้ client `web`/`tv_samsung` ถูกตัดออกและ format อาจหาย ให้เลือกทางใดทางหนึ่ง
   - ทาง A (แนะนำตาม wiki): `pip install -U "yt-dlp[default,curl-cffi]"` แล้วติดตั้ง Deno ≥ 2.3.0 (`winget install DenoLand.Deno` **[ข้อเสนอ — ไม่ได้ยืนยัน package id]**)
   - ทาง B (ไม่ต้องลงอะไรเพิ่ม): `pip install -U "yt-dlp[default,curl-cffi]"` แล้วใส่ `--js-runtimes node` ในทุกคำสั่งหรือในไฟล์ config ของ yt-dlp (Node 24.15 ผ่านขั้นต่ำ v22)
   - ควรเรียก yt-dlp ผ่าน `python -m yt_dlp` ใน venv ของ plugin และ pin เวอร์ชันพร้อม `yt-dlp-ejs` ที่ตรงกัน **[ข้อเสนอ]**
2. **List ช่อง** (เร็ว ใช้ request น้อย):
   ```
   yt-dlp --js-runtimes node --flat-playlist -J --extractor-args "youtubetab:approximate_date" "https://www.youtube.com/channel/<UCID>/videos"
   yt-dlp --js-runtimes node --flat-playlist -J --extractor-args "youtubetab:approximate_date" "https://www.youtube.com/channel/<UCID>/shorts"
   ```
3. **ดึงซับ + metadata ไม่โหลดวิดีโอ** (ต่อคลิป หรือส่งเป็น batch file):
   ```
   yt-dlp --js-runtimes node --skip-download --write-info-json \
     --write-subs --write-auto-subs --sub-langs "<รายการภาษาที่ระบุแน่นอน>" --sub-format "vtt/best" \
     -t sleep --sleep-requests 1.5 -i --download-archive "<cache>/<handle>/archive.txt" \
     -o "<cache>/<handle>/%(upload_date)s_%(id)s.%(ext)s" -a ids.txt
   ```
   - **ห้ามใช้ `--sub-langs all`** และหลีกเลี่ยง regex กว้างๆ อย่าง `en.*` เพราะจะไปจับ auto-caption ที่แปลแล้ว ซึ่งเป็นตัวที่โดน 429 ให้ใช้ `--list-subs` กับคลิปตัวอย่างก่อน แล้วระบุภาษาต้นฉบับให้ชัด **[ข้อเสนอ อิงจาก #13831]**
   - ตาม rate limit ของ guest (~300 วิดีโอ/ชม.) ช่องที่มี 1000 คลิปจะใช้เวลาอย่างน้อยราว 3–4 ชม. ต่อรอบเต็ม ดังนั้น resume ผ่าน `--download-archive` + `state.json` ต้องทำงานจริง
   - **ไม่ใช้ cookies เป็นค่าเริ่มต้น** (ขอบเขตของโปรเจกต์ข้าม members-only และ age-restricted อยู่แล้ว) · ถ้าเจอ bot check ให้หยุด รอ แล้ว fallback ไป NexLev ตามที่ PLAN วางไว้
   - ถ้าเจอข้อความ `Sign in to confirm you're not a bot` / `This content isn't available, try again later` / 429 ให้ backoff ทั้งงาน (ไม่ใช่แค่ retry ทีละคลิป) แล้วบันทึกลง `skipped.md` ว่า "rate-limited" แทน "ไม่มีซับ" **[ข้อเสนอ]**
4. **วิดีโอ 360p สำหรับดึงเฟรม** (ไม่ต้องใช้เสียง ไม่ต้อง merge จึงไม่ต้องใช้ ffmpeg ตอนดาวน์โหลด):
   ```
   yt-dlp --js-runtimes node -f "bv*[height<=360]/b[height<=360]/wv*" -S "res:360,+size" -o "<cache>/%(id)s.%(ext)s" <URL>
   ```
5. ถ้าดึงซับไม่ได้เพราะ PO Token (client `web` ต้องใช้ PO Token กับ Subs) ให้ติดตั้ง plugin `bgutil-ytdlp-pot-provider` เป็นทางเลือกที่สอง ไม่ต้องใส่ตั้งแต่แรก **[ข้อเสนอ]**

### Unconfirmed / open
- ยังไม่รู้ว่าซับในโหมด default client (ไม่มี PO Token) ดึงจาก client ไหน และ client นั้นต้องใช้ PO Token กับ Subs หรือไม่ · wiki บอกแค่ว่า `web` ต้องใช้ ต้องลองด้วย `-v --list-subs` ใน prototype
- ยังไม่ยืนยันจากเอกสารว่า YouTube สร้าง auto-caption ภาษาไทยให้คลิปส่วนใหญ่ และ track ภาษาต้นฉบับใช้รหัสอะไร (เช่น `th` หรือ `th-orig`) ต้องดูจาก `--list-subs` ของช่องไทยจริง
- `--sleep-interval` ทำงานเมื่อใช้ `--skip-download` หรือไม่ README บอกแค่ว่า "before each download" ยังไม่ได้ยืนยัน
- ตัวเลข rate limit (~300 และ ~2000 วิดีโอ/ชม.) มาจาก wiki ที่ไม่มีวันที่กำกับ YouTube เปลี่ยนได้ตลอด
- package id ของ Deno บน winget ยังไม่ได้ตรวจจาก winget-pkgs

---

## 2. Whisper สำหรับภาษาไทย — faster-whisper large-v3 / turbo vs Thonburian

### Findings

**ความแม่นยำภาษาไทย (WER ตัดคำด้วย deepcut)**
- paper Thonburian Whisper (ICNLSP 2024) Table 1 เทียบ "Vanilla (L)" ซึ่งคือ Whisper large **v3** (paper ระบุว่าใช้ "small, medium, and large (v3)") กับ Thonburian (L) — https://aclanthology.org/2024.icnlsp-1.17.pdf
  | ชุดทดสอบ | Vanilla large-v3 WER | Thonburian large WER |
  |---|---|---|
  | Common Voice 13 test | 12.8 | 5.5 |
  | FLEURS test | 14.7 | 8.7 |
  | Thai Central dev (สำเนียงกลาง) | 37.9 | 6.0 |
  | OOD การเงิน (zero-shot, Table 2) | 25.2 | 18.7 |
- GitHub README ของ Thonburian ระบุ WER บน CV13: large-v3 **6.59**, medium 7.42, distilled large 6.82, medium-timestamp 15.57 (ตัวเลขต่างจาก paper เล็กน้อย ต่าง checkpoint/รอบ) — https://github.com/biodatlab/thonburian-whisper และ https://huggingface.co/biodatlab/whisper-th-large-v3-combined
- ข้อควรระวัง: Thonburian fine-tune ด้วย Common Voice 13, FLEURS และ Thai dialect corpus จึงได้เปรียบบนชุดทดสอบเหล่านี้ · ตัวเลข OOD การเงิน (25.2 → 18.7) น่าจะใกล้กับเนื้อหา YouTube จริงกว่า — https://github.com/biodatlab/thonburian-whisper และ paper ข้างต้น
- **large-v3-turbo**: OpenAI ระบุว่าโดยรวมทำได้ใกล้ large-v2 "though it shows larger degradation on some languages like Thai and Cantonese" (ตัด decoder จาก 32 เหลือ 4 layer) — https://github.com/openai/whisper/discussions/2363 · https://huggingface.co/openai/whisper-large-v3-turbo
- faster-whisper เขียนไว้ว่าให้ "the same accuracy" เท่ากับ openai/whisper และเร็วกว่าถึง 4 เท่า — https://github.com/SYSTRAN/faster-whisper

**Timestamps (สำคัญสำหรับลิงก์ `?t=`)**
- โมเดล Thonburian มาตรฐานแนะนำ "for general Thai ASR tasks where timestamps are not required" · มีโมเดลแยก `whisper-th-medium-timestamp` (WER 15.57) · สำหรับไฟล์ยาวแนะนำ VAD + chunking — https://github.com/biodatlab/thonburian-whisper
- `BatchedInferencePipeline.transcribe` ของ faster-whisper ตั้งค่าเริ่มต้น `without_timestamps=True` และ `vad_filter=True` (ตัด chunk ตาม VAD ยาวไม่เกิน `chunk_length`) — https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py

**ใช้ Thonburian กับ faster-whisper / CTranslate2**
- biodatlab **ไม่มี** repo CTranslate2 อย่างเป็นทางการ (ทุกโมเดลเป็น transformers/safetensors) — https://huggingface.co/biodatlab
- faster-whisper มีคำสั่งแปลงโมเดล Whisper ที่ fine-tune ด้วย transformers: `ct2-transformers-converter --model <hf-id> --output_dir <dir> --copy_files tokenizer.json preprocessor_config.json --quantization float16` แล้วโหลดด้วย `WhisperModel("<dir>")` — https://github.com/SYSTRAN/faster-whisper#model-conversion
- มีตัวแปลงจาก community บน HF เช่น `Vinxscribe/biodatlab-whisper-th-large-v3-faster` (library: ctranslate2, base_model = biodatlab/whisper-th-large-v3-combined, 2025-04-11) และ `CodeHardThailand/whisper-th-large-v3-combined-ct2` (2024-05-27) **เป็นของบุคคลที่สาม ไม่ใช่ biodatlab** — https://huggingface.co/Vinxscribe/biodatlab-whisper-th-large-v3-faster

**VRAM บน GPU 8GB**
- benchmark ใน README (large-v2 ซึ่งมีจำนวน parameter ใกล้ large-v3, RTX 3070 Ti 8GB, ถอดเสียง 13 นาที): fp16 beam5 = 4525MB · int8 = 2926MB · fp16 `batch_size=8` = 6090MB (17 วินาที) · int8 batch 8 = 4500MB — https://github.com/SYSTRAN/faster-whisper#benchmark
- compute_type ที่ README ใช้: `float16`, `int8_float16` (GPU), `int8` (CPU) — https://github.com/SYSTRAN/faster-whisper#usage
- Thonburian (large) ใช้ memory 6025MB ที่ fp32 บน A100 (transformers) — https://github.com/biodatlab/thonburian-whisper

**Windows + CUDA**
- faster-whisper ต้องใช้ cuBLAS สำหรับ CUDA 12 และ cuDNN 9 · "The latest versions of ctranslate2 only support CUDA 12 and cuDNN 9" · วิธีติดตั้ง nvidia-* ผ่าน pip ในหน้า README ระบุว่า **"Linux only"** · บน Windows แนะนำไลบรารีจาก Purfview `whisper-standalone-win` (ชุด `CUDA12_v3` = cuBLAS 12.8.4.1 + cuDNN 9.8.0.87) แล้ววางไว้ใน PATH — https://github.com/SYSTRAN/faster-whisper#gpu · https://github.com/Purfview/whisper-standalone-win/releases/tag/libs
- faster-whisper **ไม่ต้องใช้ ffmpeg ระดับระบบ** เพราะถอดรหัสเสียงด้วย PyAV — https://github.com/SYSTRAN/faster-whisper#requirements
- **อัปเดตใหม่กว่า README:** CTranslate2 `v4.6.3` (2026-01-06) เพิ่ม "Conv1d pure CUDA implementation … makes cuDNN an optional dependency" และ build script ของ wheel Windows ใช้ `-DWITH_CUDNN=OFF`, CUDA 12.8, `CUDA_DYNAMIC_LOADING=ON` — https://github.com/OpenNMT/CTranslate2/blob/master/CHANGELOG.md · https://github.com/OpenNMT/CTranslate2/commit/166b731eccb87599164d6c368d1dc6d815345673 · https://github.com/OpenNMT/CTranslate2/blob/master/python/tools/prepare_build_environment_windows.sh
- CTranslate2 `4.8.5` (2026-11-02) มี wheel Windows สำหรับ cp312 · ต้องมี Visual C++ runtime บน Windows — https://pypi.org/project/ctranslate2/4.8.5/ · https://github.com/OpenNMT/CTranslate2/blob/master/docs/installation.md
- หน้า installation ของ CTranslate2 ยังเขียนว่า "cuDNN 8" ซึ่งล้าสมัยและขัดกับ CHANGELOG (4.5.0 ย้ายไป cuDNN 9 แล้ว ส่วน 4.6.3 ทำให้ cuDNN เป็น optional) — https://github.com/OpenNMT/CTranslate2/blob/master/docs/installation.md
- `nvidia-cublas-cu12` เวอร์ชันล่าสุด `12.9.3.13` (2026-10-30) **ไม่มี wheel win_amd64** · เวอร์ชัน `12.9.2.10` และเก่ากว่ามี win_amd64 · `nvidia-cudnn-cu12 9.28.1.4` มี win_amd64 — https://pypi.org/project/nvidia-cublas-cu12/#files · https://pypi.org/project/nvidia-cudnn-cu12/#files
- faster-whisper `1.2.1` ต้องใช้ `ctranslate2>=4.0,<5` — https://pypi.org/project/faster-whisper/1.2.1/

### Implications for Brain Sucker

1. **ใช้ซับของ YouTube ก่อน Whisper ทุกครั้ง** ตามที่ PLAN วางไว้ ถูกต้องแล้ว
2. **ภาษาอังกฤษ:** `large-v3` (ความแม่นยำสูงสุด) หรือ `turbo` (เร็วกว่า) ผ่าน faster-whisper ใช้ `compute_type="float16"`, `BatchedInferencePipeline(batch_size=8)` (~6GB, พอดี 8GB)
3. **ภาษาไทย: ห้ามใช้ turbo** (OpenAI ยืนยันเองว่าแย่ลงในภาษาไทย) ให้เลือกระหว่าง
   - Thonburian large-v3 แปลงเป็น CTranslate2 เอง (`ct2-transformers-converter ... --quantization float16`) ไม่พึ่ง repo community · ได้ WER ดีกว่า vanilla มากตาม paper
   - vanilla `large-v3` เป็นตัว baseline
   - ใน prototype ขั้นที่ 1 ให้วัดทั้งสองตัวกับคลิปไทยจริง 1–2 คลิป เทียบกับซับ manual (ถ้ามี)
4. **Timestamp:** ใช้ `BatchedInferencePipeline` (VAD chunk) เพื่อได้ timestamp ระดับ chunk ≤30 วินาที ซึ่งพอสำหรับลิงก์ `?t=` · ไม่ควรพึ่ง timestamp token ของ Thonburian **[ข้อเสนอ]**
5. **ติดตั้งบน Windows** **[ข้อเสนอ ต้องยืนยันใน prototype]**
   ```
   pip install faster-whisper            # ดึง ctranslate2 4.8.x มาด้วย
   pip install "nvidia-cublas-cu12==12.9.2.10"   # ตัวล่าสุดไม่มี wheel Windows
   # ก่อน import faster_whisper:
   #   os.add_dll_directory(<site-packages>/nvidia/cublas/bin)  หรือเพิ่ม path นี้เข้า PATH
   ```
   ทางสำรองตาม README: ดาวน์โหลด `cuBLAS.and.cuDNN_CUDA12_win_v3.7z` ของ Purfview (809MB) แล้วแตกไฟล์ไว้ในโฟลเดอร์ที่อยู่ใน PATH (ไม่ควรวางใน System32)
6. ffmpeg ยังต้องติดตั้งสำหรับ scene detection และ yt-dlp `--convert-subs` แต่ **ไม่จำเป็นสำหรับ faster-whisper**
7. **ไม่โหลด Whisper และ PaddleOCR GPU ไว้ใน process เดียวกันพร้อมกัน** บน 8GB ควรประมวลผลทีละ stage **[ข้อเสนอ]**

### Unconfirmed / open
- ยังไม่มีตัวเลข WER ภาษาไทยของ vanilla large-v3 จากเอกสารของ OpenAI เอง (กราฟใน discussion #1762/#2363 เป็นรูปภาพ อ่านค่าไม่ได้) ตัวเลขที่มีมาจาก paper Thonburian เท่านั้น
- ไม่มีตัวเลข VRAM ของ large-v3 / Thonburian-CT2 จาก faster-whisper โดยตรง (มีแค่ large-v2) ต้องวัดเอง
- ยังไม่ได้ยืนยันว่า wheel `nvidia-cublas-cu12==12.9.2.10` บน Windows วาง `cublas64_12.dll` ไว้ที่ `nvidia/cublas/bin` และ ctranslate2 โหลดได้ผ่าน `os.add_dll_directory` ต้องลองใน prototype
- ยังไม่ยืนยันว่า wheel ctranslate2 ที่ build ด้วย `CMAKE_CUDA_ARCHITECTURES` สูงสุด 86 ทำงานบน RTX 4070 (sm_89) ได้เต็มประสิทธิภาพ (โดยหลักน่าจะใช้ได้ แต่ยังไม่ได้ยืนยัน)
- ยังไม่ยืนยันจากหน้า compatibility ของ NVIDIA ว่า driver 591.86 (CUDA 13.1) รันแอป CUDA 12.8 ได้ หน้านั้นไม่ได้เขียนถึงกรณีนี้ตรงๆ
- คุณภาพของ Thonburian กับเสียงพูดเร็วและเสียงเพลงประกอบในคลิปทำอาหาร ไม่มีข้อมูล ต้องวัดเอง

---

## 3. OCR ข้อความไทยบนจอ + ffmpeg scene detection

### Findings

**PaddleOCR**
- PaddleOCR `3.2.0` (2025-08-21) เพิ่มโมเดล recognition PP-OCRv5 ภาษาอังกฤษ ไทย และกรีก · โมเดลไทยมี accuracy **82.68%** (กรีก 89.28%) — https://github.com/PaddlePaddle/PaddleOCR (README, release notes 3.2.0)
- โมเดลไทยคือ `th_PP-OCRv5_mobile_rec` ขนาด 7.5MB "supports recognition of Thai, English, and numbers" (มีเฉพาะรุ่น mobile) — https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/OCR.en.md
- ตารางเวอร์ชันกับภาษา: `th` อยู่ในแถว **PP-OCRv5** · **PP-OCRv6 (ตัวใหม่ล่าสุดใน 3.7.0) ไม่รองรับไทย** (รองรับ 50 ภาษา: จีน อังกฤษ ญี่ปุ่น และอักษรละติน) — https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/OCR.en.md (Appendix) · https://github.com/PaddlePaddle/PaddleOCR (release 3.7.0)
- เลือกภาษาด้วยพารามิเตอร์ `lang` และ `ocr_version` ("not every ocr_version supports all lang options") — https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/OCR.en.md
- PaddleOCR-VL (VLM 0.9B) รองรับ 109–111 ภาษา รวมภาษาไทย (เป็น document parser ที่หนักกว่า) — https://github.com/PaddlePaddle/PaddleOCR
- ติดตั้ง: `python -m pip install paddleocr` + engine แยกต่างหาก · 3.5+ รองรับ engine `paddle`, `transformers`, `onnxruntime` · แนะนำ "install only one inference engine per environment" — https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/installation.en.md · https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/inference_deployment/local_inference/inference_engine.en.md
- PaddlePaddle GPU ผ่าน pip: `python -m pip install paddlepaddle-gpu==3.2.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/` (driver ≥ 550.54.14) · "You do not need to pay attention to the physical machine's CUDA version. You only need to care about the GPU driver version." · wheel พิเศษสำหรับ Windows มีแค่ RTX **50**-series — https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/paddlepaddle_installation.en.md
- PaddleOCR 3.7.x ต้องใช้ PaddlePaddle ≥ 3.0.0 · Python ≥ 3.8 — https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/paddleocr_and_paddlex.en.md · https://pypi.org/project/paddleocr/
- engine ONNX Runtime: `python -m pip install onnxruntime-gpu` (CUDA 12.x) — https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/inference_deployment/local_inference/inference_engine.en.md

**EasyOCR**
- รองรับไทย (`th`) ผ่านโมเดลรุ่นเก่า `thai_g1` (gen1, ไฟล์จาก release `pre-v1.1.6`) · ใช้ร่วมได้แค่กับ `['th','en']` — https://github.com/JaidedAI/EasyOCR/blob/master/easyocr/easyocr.py · https://github.com/JaidedAI/EasyOCR/blob/master/easyocr/config.py
- บน Windows ต้องติดตั้ง torch/torchvision ตามเวอร์ชัน CUDA เองก่อน — https://github.com/JaidedAI/EasyOCR#installation
- release ล่าสุดคือ 1.7.2 (2024-09-24) · commit ล่าสุดคือ 2025-12-05 (แก้ README) · issue เปิดค้าง 535 รายการ — https://pypi.org/project/easyocr/ · https://github.com/JaidedAI/EasyOCR
- EasyOCR ไม่ได้เผยตัวเลขความแม่นยำภาษาไทย — (ไม่พบใน README)

**Tesseract**
- มี `tha.traineddata` ใน `tessdata`, `tessdata_best`, `tessdata_fast` — https://github.com/tesseract-ocr/tessdata_best/blob/main/tha.traineddata
- บน Windows ใช้ installer จาก UB Mannheim ตามที่ tessdoc แนะนำ (release ล่าสุด v5.4.0.20240606 ขณะที่ upstream อยู่ที่ 5.5.4, 2026-10-28) — https://github.com/tesseract-ocr/tessdoc/blob/main/Installation.md · https://github.com/UB-Mannheim/tesseract/releases
- ไม่มีตัวเลขความแม่นยำภาษาไทยจากแหล่งปฐมภูมิที่พบ

**ffmpeg scene detection**
- ตัวแปร `scene` ของ filter `select` ให้ค่า 0–1 ว่าเฟรมนี้น่าจะเป็นฉากใหม่แค่ไหน · ตัวอย่างทางการ `select='gt(scene\,0.4)'` และ "Comparing scene against a value between 0.3 and 0.5 is generally a sane choice." — https://ffmpeg.org/ffmpeg-filters.html#select_002c-aselect
- ตัวอย่างเลือกเฟรมห่างกันอย่างน้อย 10 วินาที: `select='isnan(prev_selected_t)+gte(t-prev_selected_t\,10)'` — https://ffmpeg.org/ffmpeg-filters.html#select_002c-aselect
- filter `scdet`: threshold เป็นเปอร์เซ็นต์ ค่าที่ดีคือ 8.0–14.0 (default 10) · `sc_pass=1` ส่งผ่านเฉพาะเฟรมที่เปลี่ยนฉาก · เขียน metadata `lavfi.scd.score`/`lavfi.scd.time` — https://ffmpeg.org/ffmpeg-filters.html#scdet-1
- `mpdecimate` ทิ้งเฟรมที่ต่างจากเฟรมก่อนหน้าน้อย (ใช้ dedupe ได้) — https://ffmpeg.org/ffmpeg-filters.html#mpdecimate
- `showinfo` พิมพ์ `n`, `pts`, `pts_time` ของแต่ละเฟรม (ใช้ map เฟรมกลับเป็น timestamp) — https://ffmpeg.org/ffmpeg-filters.html#showinfo
- `-fps_mode vfr` ส่งเฟรมพร้อม timestamp เดิม (เอกสารปัจจุบันไม่มี `-vsync` แล้ว) — https://ffmpeg.org/ffmpeg.html#Advanced-Video-options
- build สำหรับ Windows ที่ ffmpeg.org ชี้ไป: gyan.dev และ BtbN — https://ffmpeg.org/download.html · winget-pkgs มี manifest `Gyan.FFmpeg` (ล่าสุดคือ 9.0.2) — https://github.com/microsoft/winget-pkgs/tree/master/manifests/g/Gyan/FFmpeg

### Implications for Brain Sucker

1. **PaddleOCR ใช้กับไทยได้จริง แต่ต้อง pin** `PaddleOCR(lang="th", ocr_version="PP-OCRv5")` (หรือระบุ `text_recognition_model_name="th_PP-OCRv5_mobile_rec"`) เพราะค่าเริ่มต้นใหม่คือ PP-OCRv6 ที่ไม่มีไทย · accuracy 82.68% แปลว่าข้อความบนจอภาษาไทยจะมีผิดบ้าง ให้ถือเป็น "หลักฐานเสริม" ไม่ใช่ข้อเท็จจริงหลัก
2. **เส้นทางติดตั้งบน Windows** **[ข้อเสนอ]** แยก venv จาก faster-whisper เพราะเอกสารเตือนว่า engine ชนกันได้ และ CUDA DLL ของ Paddle กับ CTranslate2 อาจชนกัน
   - เริ่มด้วย CPU ก่อน (`pip install paddleocr paddlepaddle`) เพราะโมเดล mobile เล็ก (7.5MB) และจำนวนเฟรมต่อคลิปหลัง dedupe น่าจะน้อย ถ้าช้าเกินไปค่อยเปลี่ยนเป็น `paddlepaddle-gpu==3.2.0 -i .../cu126/` (driver 591.86 ผ่านขั้นต่ำ 550.54.14)
3. **ทางเลือกสำรอง:** Tesseract `tha` (ติดตั้งง่ายสุดบน Windows แต่ใช้ CPU อย่างเดียว ไม่มีตัวเลขความแม่นยำ) ใช้เป็นตัวเทียบใน prototype · EasyOCR **ไม่แนะนำ** (โมเดลไทยรุ่น gen1 เก่า โปรเจกต์ไม่ค่อยเคลื่อนไหว ต้องลง torch เพิ่ม)
4. **pipeline เฟรม:**
   ```
   ffmpeg -hide_banner -i in.mp4 -vf "select='gt(scene,0.3)',showinfo" -fps_mode vfr "<cache>/frames/%05d.jpg"
   ```
   แล้ว parse `pts_time` จาก stderr ของ showinfo เพื่อผูก timestamp · dedupe ด้วย perceptual hash หรือเทียบข้อความ OCR ซ้ำ **[ข้อเสนอ]** · ถ้าคลิปเป็นกล้องนิ่งพร้อม text overlay ที่ scene score ต่ำ ให้เพิ่มการสุ่มเฟรมทุก N วินาที (`isnan(prev_selected_t)+gte(t-prev_selected_t\,N)`)
5. ติดตั้ง ffmpeg ด้วย `winget install Gyan.FFmpeg` ตามที่ PLAN วางไว้ (มี manifest จริง)

### Unconfirmed / open
- ยังไม่ยืนยันว่ามี wheel `paddlepaddle-gpu==3.2.0` cu126 สำหรับ **Windows + cp312** บน index ของ Paddle (เอกสารให้แค่คำสั่ง ไม่มีตาราง OS/Python) และยังไม่ยืนยันว่ารองรับ RTX 4070 Laptop
- ไม่รู้ว่า "accuracy 82.68%" วัดจากชุดข้อมูลแบบไหน (เอกสาร, ฉาก, ข้อความบนวิดีโอ) และเป็น line accuracy หรือไม่
- ยังไม่ยืนยันว่า engine `onnxruntime` ใช้ `th_PP-OCRv5_mobile_rec` ได้ทันทีหรือต้อง export เอง
- ไม่มี benchmark จากแหล่งปฐมภูมิที่เทียบ PaddleOCR / EasyOCR / Tesseract บนข้อความไทยในวิดีโอ ต้องวัดเองใน prototype
- threshold 0.3 สำหรับคลิปทำอาหาร (กล้องเคลื่อนตลอด) อาจได้เฟรมมากเกินไป ต้องจูน

---

## 4. Claude Code plugin — โครงสร้าง, local marketplace, scripts, subagent Haiku

### Findings

**โครงสร้าง plugin**
- manifest อยู่ที่ `.claude-plugin/plugin.json` (ไม่บังคับต้องมี, บังคับแค่ `name`) · ไฟล์อื่นทั้งหมด (`skills/`, `commands/`, `agents/`, `hooks/`) อยู่ที่ root ของ plugin **ไม่ใช่** ใน `.claude-plugin/` — https://code.claude.com/docs/en/plugins-reference.md (หัวข้อ Manifest file, Fields)
- ตำแหน่งมาตรฐาน: `skills/<name>/SKILL.md`, `commands/` (แนะนำให้ใช้ skills แทนใน plugin ใหม่), `agents/*.md`, `hooks/hooks.json`, `.mcp.json`, `bin/` (ไฟล์ในนี้อยู่บน PATH ของ Bash tool ตอนที่ plugin เปิดอยู่), `settings.json`, `workflows/` — https://code.claude.com/docs/en/plugins-reference.md#standard-layout
- "A `CLAUDE.md` at the plugin root isn't loaded as context, and `claude plugin validate` warns when it finds one." — https://code.claude.com/docs/en/plugins-reference.md#standard-layout
- skill ใน plugin ถูก namespace เป็น `/plugin-name:skill-name` · ถ้ายังไม่มีคำสั่งอื่นใช้ชื่อเดียวกัน ก็พิมพ์ชื่อสั้นได้ด้วย ("The bare `/fancy` also invokes the skill unless another command already uses that name.") — https://code.claude.com/docs/en/skills.md#how-a-skill-gets-its-command-name

**Local marketplace + ติดตั้งระดับ user**
- marketplace คือโฟลเดอร์ที่มี `.claude-plugin/marketplace.json` ซึ่งต้องมี `name`, `owner`, `plugins[]` (แต่ละตัวมี `name`, `source`) · `source` แบบ relative ต้องขึ้นต้นด้วย `./` และนับจาก marketplace root (โฟลเดอร์ที่มี `.claude-plugin/`) · ห้ามใช้ `..` · `"."`/`"./"` = ตัว root เอง — https://code.claude.com/docs/en/plugin-marketplaces.md · https://code.claude.com/docs/en/plugins/marketplace-reference.md
- คำสั่ง: `claude plugin validate ./my-marketplace` → `claude plugin marketplace add ./my-marketplace` (บันทึกลง user settings) → `claude plugin install <plugin>@<marketplace>` (แสดง `scope: user`) → `claude plugin list` · `--scope` เลือกได้ `user|project|local` ค่าเริ่มต้นคือ `user` — https://code.claude.com/docs/en/plugin-marketplaces.md · https://code.claude.com/docs/en/plugins/cli-reference.md
- ชื่อ entry ใน marketplace.json ควรตรงกับ `name` ใน plugin.json — https://code.claude.com/docs/en/plugin-marketplaces.md#keep-the-entry-name-and-the-manifest-name-the-same
- plugin แบบ relative-path ใน marketplace ที่ add จาก local path จะ **โหลดจากที่อยู่เดิมโดยตรง** (ไม่ copy ไป cache) · แก้ไฟล์แล้วมีผลเมื่อเริ่ม session ใหม่หรือรัน `/reload-plugins` · ไม่ต้องเปลี่ยน version · Claude Code จะไม่ติดตั้ง dependency ให้ในโฟลเดอร์ต้นทาง — https://code.claude.com/docs/en/plugins/loading.md
- ระหว่างพัฒนาใช้ `--plugin-dir` ได้ (โหลดจากที่อยู่เดิม) — https://code.claude.com/docs/en/plugins/loading.md · https://code.claude.com/docs/en/plugin-marketplaces.md

**อ้างถึง script ที่แนบมากับ plugin**
- `${CLAUDE_PLUGIN_ROOT}` = path จริงของ plugin ที่ติดตั้ง (เปลี่ยนเมื่ออัปเดต จึง **ห้ามเขียน state ไว้ที่นี่**) · `${CLAUDE_PLUGIN_DATA}` = `~/.claude/plugins/data/<id>/` อยู่ข้ามการอัปเดต ใช้เก็บ dependency และ cache — https://code.claude.com/docs/en/plugins-reference.md#environment-variables
- ใน skill/agent markdown, `${CLAUDE_PLUGIN_ROOT}` ถูกแทนค่าแบบ inline ในเนื้อหา · **ตัวแปรเหล่านี้ไม่อยู่ใน environment ของคำสั่ง Bash ที่ Claude รัน** — https://code.claude.com/docs/en/plugins-reference.md#where-each-variable-resolves
- `${CLAUDE_PLUGIN_ROOT}`/`${CLAUDE_PLUGIN_DATA}` ถูกแทนค่าใน `allowed-tools` ของ skill ด้วย จึงอนุญาตล่วงหน้าให้ script รันโดยไม่ต้องถาม เช่น `allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/render.sh *)` · `${CLAUDE_SKILL_DIR}` คือโฟลเดอร์ของ SKILL.md — https://code.claude.com/docs/en/skills.md#available-string-substitutions
- บน Windows ค่า path ที่แทนส่วนใหญ่ใช้ `/` (เช่น `C:/Users/you/...`) · ควรครอบด้วย double quotes เพื่อให้ path ที่มีช่องว่างยังเป็น argument เดียว — https://code.claude.com/docs/en/plugins-reference.md#quoting-and-path-separators

**Subagent ที่ระบุ model (Haiku)**
- frontmatter ของ subagent: `model` รับ `sonnet`, `opus`, `haiku`, `fable`, model ID เต็ม หรือ `inherit` — https://code.claude.com/docs/en/sub-agents.md#frontmatter-reference
- ลำดับการเลือก model: (1) พารามิเตอร์ `model` ตอนเรียก Agent tool (รับแค่ alias) → (2) `model` ใน frontmatter → (3) `CLAUDE_CODE_SUBAGENT_MODEL` → (4) model ของ session หลัก — https://code.claude.com/docs/en/sub-agents.md#choose-a-model
- agent ใน plugin อยู่ที่ `agents/*.md` ชื่อเต็มคือ `<plugin>:<name>` · field ที่รองรับ: `name`, `description`, `model`, `effort`, `maxTurns`, `tools`, `disallowedTools`, `skills`, `memory`, `background`, `omitClaudeMd`, `isolation` ฯลฯ · **ไม่รองรับ** `hooks`, `mcpServers`, `permissionMode` — https://code.claude.com/docs/en/plugins/components.md#agents · https://code.claude.com/docs/en/sub-agents.md#choose-the-subagent-scope
- skill ที่ตั้ง `context: fork` จะรันใน subagent (ตั้ง `agent:` เลือกประเภทได้ และ `model:` จะเป็น model ของ subagent นั้น) · รันเป็น background โดยค่าเริ่มต้น ตั้ง `background: false` เพื่อรอผล — https://code.claude.com/docs/en/skills.md#run-skills-in-a-subagent · https://code.claude.com/docs/en/skills.md#frontmatter-reference
- `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` จะทำให้ไม่สนใจ `model` ใน frontmatter (ถ้าผู้ใช้ตั้งไว้ Haiku จะไม่ถูกใช้) — https://code.claude.com/docs/en/sub-agents.md#run-every-subagent-on-one-model
- **Workflows** (`workflows/*.js` ใน plugin, namespace เป็น `/plugin:name`): ใช้ `agent()`, `pipeline()`, `parallel()` · ค่าเริ่มต้นรัน 16 agent พร้อมกัน · **ไม่เกิน 4,096 item ต่อ `pipeline()` และไม่เกิน 1,000 agent ต่อ run** · ถ้าชน usage limit run จะหยุดรอ (เฉพาะ session แบบ interactive ที่ใช้ claude.ai subscription) · model ที่ script ระบุให้ stage นับเป็น per-invocation model — https://code.claude.com/docs/en/workflows.md

### Implications for Brain Sucker

1. **โครงสร้างที่แนะนำ** (ให้โฟลเดอร์ `brain sucker` เป็น marketplace และวาง plugin ไว้ในโฟลเดอร์ย่อย เพื่อไม่ให้ `docs/`, `CLAUDE.md` ของ dev และ `.git` ปนกับ plugin root) **[ข้อเสนอ]**
   ```
   brain sucker/                       ← marketplace root + repo
   ├── .claude-plugin/marketplace.json  {"name":"brain-sucker-local","owner":{"name":"..."},
   │                                     "plugins":[{"name":"brain-sucker","source":"./plugins/brain-sucker"}]}
   ├── docs/ ...
   └── plugins/brain-sucker/
       ├── .claude-plugin/plugin.json   {"name":"brain-sucker"}
       ├── skills/brain-suck/SKILL.md    → /brain-sucker:brain-suck (และ /brain-suck ถ้าไม่ชนชื่ออื่น)
       ├── agents/video-summarizer.md   (model: haiku)
       ├── agents/synthesizer.md        (model: opus)
       ├── scripts/*.py                 (pipeline Python)
       └── templates/CLAUDE.md.tmpl     (template ของที่ปรึกษา ห้ามตั้งชื่อ CLAUDE.md ที่ plugin root)
   ```
   ติดตั้ง: `claude plugin validate "./brain sucker"` → `claude plugin marketplace add "<path>/brain sucker"` → `claude plugin install brain-sucker@brain-sucker-local` (ได้ scope user)
2. **การเรียก script:** ใน SKILL.md ให้เขียน `python "${CLAUDE_PLUGIN_ROOT}/scripts/ingest.py" ...` ตรงๆ ในเนื้อหา (Claude Code แทนค่าให้ตอนโหลด) ห้ามอ้าง `$CLAUDE_PLUGIN_ROOT` เป็น env var ใน Bash · ใส่ `allowed-tools: Bash(python "${CLAUDE_PLUGIN_ROOT}/scripts/*" *)` เพื่อลด permission prompt (ต้องทดสอบรูปแบบ pattern จริง) **[ข้อเสนอ]**
3. **venv ของ Python** (faster-whisper, PaddleOCR, yt-dlp) ให้สร้างไว้ใน `${CLAUDE_PLUGIN_DATA}` ไม่ใช่ใน plugin root · path ของ OneDrive มีช่องว่าง (`brain sucker`) ต้องครอบ quotes ทุกที่ **[ข้อเสนอ อิงจาก docs]**
4. **สรุปรายคลิปด้วย Haiku:** ประกาศ `agents/video-summarizer.md` ที่มี `model: haiku` แล้วให้ skill สั่ง Agent tool ด้วย `subagent_type: brain-sucker:video-summarizer` (หรือส่ง `model: haiku` ตอนเรียก) · ถ้าใช้ workflow เพื่อ fan-out ต้องแบ่ง batch ให้ไม่เกิน 1,000 agent ต่อ run (เช่น 1 agent สรุปหลายคลิป หรือรันเป็นหลายรอบตามการ resume ใน `state.json`)
5. agent ใน plugin ใช้ `hooks`/`mcpServers`/`permissionMode` ไม่ได้ ถ้า fallback NexLev MCP ต้องให้ session หลักเป็นคนเรียก ไม่ใช่ subagent ของ plugin (หรือประกาศ MCP ใน `.mcp.json` ของ plugin) **[ข้อเสนอ]**

### Unconfirmed / open
- ยังไม่ได้ตรวจ syntax ที่แน่นอนของการระบุ model ใน `agent()` ของ workflow (docs บอกแค่ว่า "A model the script names for a stage counts as the per-invocation model") ต้องโหลด skill `/workflow-authoring` ตอน implement
- ยังไม่ได้ทดสอบว่า `allowed-tools` pattern ที่มี `${CLAUDE_PLUGIN_ROOT}` + path ที่มีช่องว่าง + `python` ขึ้นต้น จะ match ได้จริงบน Windows หรือไม่
- ยังไม่ยืนยันว่าการโหลด plugin "in place" จากโฟลเดอร์ใน OneDrive (ไฟล์ on-demand/sync) มีปัญหาหรือไม่
- ไม่ได้ดู plugin `watch-video` ในรอบนี้ (อยู่ในขั้นที่ 1 ของ PLAN)

---

## สรุปจุดที่ขัดหรือเพิ่มเติมจาก PLAN.md

1. **yt-dlp ยังใช้งาน YouTube ได้ไม่เต็มที่บนเครื่องนี้:** ไม่มี `yt-dlp-ejs` และไม่มี Deno ต้องเพิ่มในขั้นที่ 1 ด้วย `pip install -U "yt-dlp[default,curl-cffi]"` + Deno หรือ `--js-runtimes node`
2. **Thonburian ไม่ได้ออกแบบมาสำหรับ timestamp** แต่ PLAN ต้องการลิงก์ `?t=` จึงต้องใช้ timestamp ระดับ VAD chunk (BatchedInferencePipeline) และไม่มี CT2 อย่างเป็นทางการ ต้องแปลงเอง · **turbo ห้ามใช้กับภาษาไทย**
3. **PaddleOCR ไทยใช้ได้เฉพาะ PP-OCRv5 mobile (accuracy 82.68%)** ไม่ใช่รุ่นล่าสุด (PP-OCRv6 ไม่มีไทย) ต้อง pin `ocr_version="PP-OCRv5"`
4. **faster-whisper บน Windows:** วิธี pip nvidia-* ใน README เขียนว่า "Linux only" แต่ CTranslate2 ≥ 4.6.3 ไม่ต้องใช้ cuDNN แล้ว เหลือแค่ cuBLAS 12 (wheel `nvidia-cublas-cu12` ตัวล่าสุดไม่มีบน Windows ต้อง pin `12.9.2.10` หรือใช้ libs ของ Purfview) · faster-whisper ไม่ต้องใช้ ffmpeg
5. **ชื่อคำสั่ง:** skill ใน plugin เป็น `/brain-sucker:brain-suck` ส่วน `/brain-suck` ใช้ได้เฉพาะเมื่อไม่ชนชื่อคำสั่งอื่น
6. **โฟลเดอร์ `brain sucker` = ซอร์ส plugin:** `CLAUDE.md` ที่ plugin root จะไม่ถูกโหลดและ validate จะเตือน ควรวาง plugin ไว้ใน `plugins/brain-sucker/` แล้วให้ root เป็น marketplace · template ของ `CLAUDE.md` ที่ปรึกษาต้องใช้ชื่อไฟล์อื่น
7. **ขนาดหลักพันคลิป:** workflow fan-out จำกัด 1,000 agent ต่อ run และ yt-dlp guest ~300 วิดีโอ/ชม. การ resume แบบ incremental จึงเป็นเงื่อนไขจำเป็น ไม่ใช่ส่วนเสริม
