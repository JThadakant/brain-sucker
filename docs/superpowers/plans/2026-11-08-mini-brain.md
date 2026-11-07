# Mini Brain Sucker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/mini-brain <url...>` ดึงคลิป YouTube / TikTok / Instagram เข้าคลังกลาง `Desktop\mini-brain` (transcript Whisper + ภาพ) แล้วคุยต่อได้ทันทีในโฟลเดอร์ไหนก็ได้ · `/mini-brain <คำถาม>` ตอบจากคลังพร้อม Citation · `--to <Advisor>` ส่งคลิปเข้าที่ปรึกษาของระบบหลัก

**Architecture:** ต่อยอด package `brainsuck` เดิม: seam ใหม่ `ClipSource` (yt-dlp รับ URL ทั่วไป + cookies เฉพาะ IG) ขนานกับ seam `YouTube` เดิม · `ClipLibrary` เก็บ Video Record แบบเรียบใน `clips/` + `index.md` + `config.json` · pipeline `clip()` ใช้ Whisper/frames/record codec เดิม · ฝั่ง Claude: skill ใหม่ `mini-brain` + ปรับ `video-summarizer` ให้ไม่ผูกกับอาหาร + skill `advisor` ค้น `clips/`

**Tech Stack:** Python 3.12, yt-dlp (`cookiesfrombrowser`, `ffmpeg_location`), faster-whisper large-v3 (auto language + `initial_prompt`), ffmpeg, PyYAML, pytest · Claude Code plugin (skills, agents, bin/) · NexLev MCP `watch_instagram_video_and_ask` (fallback)

**Spec:** `docs/superpowers/specs/2026-11-08-mini-brain-design.md` (หลัก) · `docs/research/0003-mini-prototype.md` · `docs/HANDOFF.md` §2 (คำตอบ grill ดิบ) · `docs/DESIGN.md` § รูปแบบ Video Record · `GLOSSARY.md`

## Global Constraints

- **ที่ทำงาน:** worktree `C:\Users\Lenovo\OneDrive\Desktop\brain-sucker-mini` บน branch `feat/mini` แตกจาก `feat/v1` (v1 Task 12 E2E ยังใช้ checkout หลักอยู่ — ห้ามสลับ branch ที่นั่น)
- **venv:** เทสใช้ `C:\brain-sucker-cache\venv-dev-mini` (editable ของ worktree `[dev,asr]`) · รันจริงจาก worktree ต้องตั้ง `BRAINSUCK_CACHE=C:/brain-sucker-cache/mini` (รูปแบบ Windows + `/`) เพื่อไม่ให้ `bin/brainsuck` ติดตั้ง editable ทับ venv ของ v1
- คำสั่งเทส: `cd plugins/brain-sucker/cli && /c/brain-sucker-cache/venv-dev-mini/Scripts/python -W error -m pytest -q` · เทสเดิม 81 ข้อต้องผ่านตลอด
- **Video Record ของ Channel ต้องเหมือนเดิมทุกไบต์**: field ใหม่ของ Clip ลงไฟล์เฉพาะเมื่อ `platform` ไม่ใช่ `None`
- คลัง: ค่าเริ่มต้น `Path.home() / "OneDrive" / "Desktop" / "mini-brain"` · env `BRAINSUCK_LIBRARY` แทนได้ · เทสใช้ `tmp_path` เท่านั้น ห้ามแตะคลังจริง
- CLI เขียนได้แค่ 3 ที่: คลัง, cache, `<Advisor>/clips/` ของ `--to` · skill **ห้ามเขียนไฟล์ลงโฟลเดอร์ปัจจุบันของผู้ใช้**
- Whisper `large-v3` ทุกคลิป ห้าม turbo · `language=None` (auto-detect) เว้นแต่ YouTube info บอกภาษา · `initial_prompt` จาก `whisper_prompt()` ยาว ≤ 300 ตัวอักษร
- บรรทัดถอดไม่ชัด: segment `avg_logprob < -1.0` → บรรทัด `[mm:ss]` นั้นลงท้าย `" ⟨ถอดไม่ชัด⟩"` · `transcript_quality` = สัดส่วนบรรทัดที่มีป้ายนี้ ปัด 2 ตำแหน่ง
- ภาพ: 360p · ffmpeg scene `threshold=0.3` · สูงสุด 40 เฟรม · เก็บที่ `<cache>/frames/<platform>_<id>/` ชื่อ `t<วินาที 5 หลัก>.jpg` · skill ลบโฟลเดอร์หลังสรุป
- Cookies: `cookiesfrombrowser` เท่านั้น · **เฉพาะ URL Instagram** · ใช้หลังลองแบบไม่ล็อกอินแล้วได้ `NeedsLogin` เท่านั้น · ลำดับ `edge → firefox → chrome` · ห้ามถาม/รับรหัสผ่านหรืออีเมล
- `config.json` ของคลัง: `{"ig_cookies": "ask" | "always", "browser": <ชื่อ browser | null>}` — ตัด `"never"` ที่ spec เขียนไว้ออก เพราะตัวเลือกที่ผู้ใช้ตกลงคือ ใช่ / ไม่ / ใช่ทุกครั้ง ("ไม่" ถามใหม่ทุกครั้ง)
- ตัวตนของ Clip = `<platform>_<id>` (Clip Key) ไม่ใช่ URL ดิบ · ชื่อไฟล์ `<key>.md` (ยังไม่ตั้งชื่อ) / `<key>__<slug>.md`
- โหลดเข้าแชท: Summary + Screen Text เสมอ · Transcript เต็มเฉพาะคลิป `duration ≤ 1800` วินาที
- UTF-8 ทุกไฟล์ · JSON `ensure_ascii=False` · path ไทย/มีช่องว่างต้องใช้ได้
- นอกขอบเขต: quality gate ของระบบหลัก (v1.1 แผนแยก) · synthesis ระดับคลัง · โฟลเดอร์ย่อย · Facebook ฯลฯ

## Review Focus

1. **URL รูปแบบต่างกันของคลิปเดียวกัน** (`youtu.be/…?si=`, `vm.tiktok.com/…` ที่ต้องตามลิงก์, IG มี `?igsh=`, วาง URL เดิมซ้ำในคำสั่งเดียว) → ต้องได้ record เดียว ไม่ถอดเสียงซ้ำ → Task 5 `test_short_link_dedup_after_info`, `test_same_url_twice_in_one_command`
2. **ชื่อที่ตั้งมีอักขระต้องห้ามของ Windows / emoji / ไทยยาวมาก / สองคลิปชื่อเดียวกัน** → ได้ไฟล์ที่ถูกต้องและแยกกัน → Task 4 `test_slugify_rules`, `test_same_name_two_clips`
3. **ชุด URL ที่มีตัวเสีย** (หน้า Facebook, ลิงก์พิมพ์ผิด, คลิปถูกลบ) → คลิปอื่นในชุดยังทำต่อ ตัวเสียรายงานเป็น skipped พร้อมเหตุผล → Task 5 `test_bad_url_skipped_others_continue`
4. **`--to` ชี้โฟลเดอร์ที่ไม่ใช่ Advisor หรือ Advisor ถูกลบทีหลัง** → อันแรก exit 3 ก่อนโหลดอะไร · อันหลังข้ามการ copy ไม่ crash → Task 6 `test_clip_to_non_advisor_exit3`, Task 4 `test_copy_skips_missing_advisor`
5. **IG `duration` เป็น null / คลิปยาว 3 ชม.** → duration มาจาก segment สุดท้าย · skill ไม่โหลด transcript เต็มเกิน 30 นาที → Task 5 `test_duration_falls_back_to_segments`, Task 7 (SKILL.md)

---

### Task 1: Worktree + Glossary + Clip fields ใน Video Record

**Files:**
- Modify: `GLOSSARY.md` (เพิ่ม **Clip**, **Clip Library**, **Clip Key**, **Display Name**; แก้ _Avoid_ ของ **Video** เป็น `episode, post (ใช้ Clip สำหรับ Video ที่ผู้ใช้ส่ง URL มาเอง)`)
- Modify: `plugins/brain-sucker/cli/src/brainsuck/models.py`, `record.py`
- Test: `plugins/brain-sucker/cli/tests/test_record.py`

ความหมายใน GLOSSARY:
- **Clip**: Video ที่ผู้ใช้ส่ง URL มาเองผ่าน mini-brain ไม่ได้มาจากการ Ingest ทั้ง Channel · มาจาก YouTube, Instagram หรือ TikTok
- **Clip Library**: โฟลเดอร์กลางเดียวที่เก็บ Video Record ของทุก Clip (`Desktop\mini-brain`) เรียกใช้ได้จากทุกโฟลเดอร์ · _Avoid_: vault, inbox
- **Clip Key**: `<platform>_<id>` ตัวตนของ Clip · _Avoid_: URL (URL หลายแบบชี้ Clip เดียวกันได้)
- **Display Name**: ชื่อที่ผู้ใช้ตั้งให้ Clip (Claude เสนอ) ใช้เป็นชื่อไฟล์และชื่อใน Citation · title จริงยังเก็บไว้

**Interfaces:**
- Produces (`models.py`):
  - `Platform = Literal["youtube", "instagram", "tiktok"]`
  - `TranscriptSource` เพิ่ม `"nexlev-description"`
  - `Segment(start: float, text: str, low_conf: bool = False)`
  - `VideoRecord` เพิ่มท้าย (มีค่าเริ่มต้นทั้งหมด): `platform: Platform | None = None`, `display_name: str | None = None`, `creator: str | None = None`, `transcript_quality: float | None = None`, `copied_to: list[str] = field(default_factory=list)` (absolute path ของ Advisor ที่ copy ไป)
- Produces (`record.py`): `_CLIP_FRONT = ["platform", "display_name", "creator", "transcript_quality", "copied_to"]` ต่อท้าย front-matter หลัง `screen_frames` **เมื่อ `r.platform is not None` เท่านั้น** · `parse_record` อ่าน key เหล่านี้ถ้ามี

- [ ] **Step 1: ตั้ง worktree + venv**
  ```bash
  cd "C:/Users/Lenovo/OneDrive/Desktop/brain sucker" && git worktree add -b feat/mini ../brain-sucker-mini feat/v1
  python -m venv "C:/brain-sucker-cache/venv-dev-mini"
  /c/brain-sucker-cache/venv-dev-mini/Scripts/python -m pip install -q -e "C:/Users/Lenovo/OneDrive/Desktop/brain-sucker-mini/plugins/brain-sucker/cli[dev,asr]"
  ```
  run คำสั่งเทส (Global Constraints) → `81 passed`
- [ ] **Step 2: แก้ GLOSSARY.md** ตามความหมายข้างบน
- [ ] **Step 3: failing tests** ใน `test_record.py`
  - `test_channel_record_has_no_clip_fields`: `render_record(make_record())` ไม่มีบรรทัดขึ้นต้น `platform:`, `display_name:`, `copied_to:`
  - `test_clip_round_trip`: `make_record(platform="tiktok", kind="short", display_name="ขายของให้คนรวย: Gary \"V\"", creator="garyvee", transcript_quality=0.25, copied_to=["C:\\x y\\ที่ปรึกษา ทดสอบ"], transcript_lines=["[00:00] hi ⟨ถอดไม่ชัด⟩"])` → `parse_record(render_record(r)) == r`
  - `test_clip_round_trip_unnamed`: `platform="instagram"`, `display_name=None`, `transcript_quality=None` → round trip เท่ากัน
- [ ] **Step 4:** run → FAIL (`unexpected keyword argument 'platform'`)
- [ ] **Step 5:** implement ใน `models.py` และ `record.py`
- [ ] **Step 6:** run เทสทั้งหมด → 84 passed
- [ ] **Step 7: commit** `feat(mini): clip fields in Video Record + glossary`

### Task 2: Whisper สำหรับ Clip — auto language, prompt, บรรทัดถอดไม่ชัด

**Files:**
- Modify: `src/brainsuck/transcript.py`, `src/brainsuck/transcribe.py`, `tests/fakes.py`
- Test: `tests/test_transcript.py`, `tests/test_transcribe.py`

**Interfaces:**
- Consumes: `Segment.low_conf` (Task 1)
- Produces (`transcript.py`):
  - `UNCLEAR = " ⟨ถอดไม่ชัด⟩"` · `UNCLEAR_LOGPROB = -1.0`
  - `format_lines(segments, window=30.0)` — เดิม + ต่อ `UNCLEAR` ท้ายบรรทัดถ้ามี segment ใดในหน้าต่างนั้น `low_conf`
  - `transcript_quality(lines: list[str]) -> float` — สัดส่วนบรรทัดที่ลงท้าย `UNCLEAR`, `round(…, 2)`, ว่าง → `0.0`
  - `whisper_prompt(title: str, creator: str, description: str) -> str` — ต่อส่วนที่ไม่ว่างด้วย `". "`; ตัด URL (`https?://\S+`) และ `#แฮชแท็ก` ออกจาก description; ยุบช่องว่าง; ตัดที่ 300 ตัวอักษร
- Produces (`transcribe.py`): `Transcriber` Protocol เพิ่ม `transcribe_clip(self, audio: Path, lang: str | None, prompt: str) -> tuple[list[Segment], str]` (คืน segments + ภาษาที่ตรวจพบ) · `FasterWhisperTranscriber.transcribe_clip` เรียก `self._pipe.transcribe(str(audio), language=lang, initial_prompt=prompt or None, batch_size=self.batch_size)` แล้วตั้ง `low_conf = s.avg_logprob < UNCLEAR_LOGPROB`
- Produces (`tests/fakes.py`): `FakeTranscriber.transcribe_clip` — นับ `calls`, เก็บ `last_prompt`, `last_lang`; คืน `[Segment(0.0, …), Segment(40.0, …)]` และภาษา `lang or self.detected` (`detected` ตั้งได้ใน `__init__`, ค่าเริ่มต้น `"en"`); `low_conf_files: set[str]` ทำให้ segment ที่สองของไฟล์นั้น `low_conf=True`; `empty_files: set[str]` คืน `[]`

- [ ] **Step 1: failing tests** (`test_transcript.py`)
  - `test_unclear_marker_on_line`: segments `[S(0,"a"), S(10,"b",low_conf=True), S(40,"c")]` → `["[00:00] a b ⟨ถอดไม่ชัด⟩", "[00:40] c"]`
  - `test_quality_share`: บรรทัด 4 บรรทัด มีป้าย 1 → `0.25` · `[]` → `0.0`
  - `test_prompt_strips_urls_and_hashtags`: `whisper_prompt("How to Launch", "Y Combinator", "Kat Mañalac https://yc.com #startup tips")` == `"How to Launch. Y Combinator. Kat Mañalac tips"`
  - `test_prompt_capped_300`: description ไทย 1,000 ตัว → `len(...) <= 300`
  - `test_prompt_skips_empty`: `whisper_prompt("", "garyvee", "")` == `"garyvee"`
- [ ] **Step 2: gpu test** (`test_transcribe.py`) `test_whisper_clip_detects_thai`: glob `C:\brain-sucker-cache\proto-mini\Instagram_*\audio.*` (skip ถ้าไม่มี) → `transcribe_clip(path, None, "Claude")` คืนภาษา `"th"` และ segments ไม่ว่าง
- [ ] **Step 3:** run → FAIL
- [ ] **Step 4:** implement ตาม Interfaces
- [ ] **Step 5:** run เทสทั้งหมด → PASS · `-m gpu` → PASS (จดใน commit message ว่า transcript มีคำว่า "Claude" หรือไม่ — ใช้ใน research ของ Task 8)
- [ ] **Step 6: commit** `feat(mini): whisper auto-language, initial prompt and unclear-line marker`

### Task 3: ClipSource seam — URL → Clip Key, info, ดาวน์โหลด, cookies IG

**Files:**
- Create: `src/brainsuck/clipsource.py`
- Modify: `src/brainsuck/youtube.py` (`UnavailableReason` เพิ่ม `"unsupported"`), `tests/fakes.py`
- Create: `tests/fixtures/clips/info/youtube_3xU050kMbHM.json`, `tiktok_7479505763950611758.json`, `instagram_DejxHqIpgBG.json`
- Test: `tests/test_clipsource.py`

**Interfaces:**
- Consumes: `Platform`, `Kind` (models) · `classify_error`, `info_from_ytdlp`, `_published`, `Unavailable`, `YouTubeError` (youtube.py) · `find_ffmpeg` (frames.py)
- Produces (`clipsource.py`):
  - `@dataclass(frozen=True) ClipKey(platform: Platform, id: str)` + property `key -> str` = `f"{platform}_{id}"`
  - `parse_clip_url(url: str) -> ClipKey | None` — ไม่ใช้เน็ต:
    - YouTube: host `youtube.com`/`www.`/`m.` path `/watch?v=`, `/shorts/`, `/live/`, `/embed/` · `youtu.be/<id>` · id = `[A-Za-z0-9_-]{11}`
    - TikTok: `tiktok.com/@<user>/video/(\d+)` · `vm.`/`vt.tiktok.com` → `None` (ต้องตามลิงก์)
    - Instagram: `instagram.com/(reel|reels|p|tv)/([A-Za-z0-9_-]+)`
    - อื่นๆ → `None`
  - `@dataclass(frozen=True) ClipInfo(key: ClipKey, url: str, title: str, description: str, creator: str, published: date, duration: int, kind: Kind, lang: str | None)`
  - `clip_info_from_ytdlp(d: dict) -> ClipInfo` — platform จาก `extractor_key` (`Youtube`/`TikTok`/`Instagram`) อื่นๆ → `Unavailable("unsupported")` · YouTube: ใช้ `info_from_ytdlp(d, None)` (ได้การเช็ค members/live/private + kind) และ `lang = d.get("language")` หรือ key `<x>-orig` ใน `automatic_captions` ไม่งั้น `None` · TikTok/IG: `kind="short"`, `lang=None` · `creator = uploader or channel or uploader_id or ""` · `duration = int(d.get("duration") or 0)` · IG ที่ title ขึ้นต้น `"Video by "` → title = บรรทัดแรกที่ไม่ว่างของ description ตัดที่ 100 ตัว (ถ้า description ว่าง ใช้ title เดิม)
  - `class NeedsLogin(YouTubeError)` · `classify_clip_error(message: str, platform: Platform | None) -> YouTubeError` — ถ้า platform เป็น `instagram` และข้อความ (lower) มี `"login required"`, `"log in"`, `"cookies"`, `"empty media response"` → `NeedsLogin`; ไม่งั้น `classify_error(message)`
  - `class ClipSource(Protocol)`: `fetch_info(url: str, cookies: str | None = None) -> ClipInfo` · `fetch_audio(url: str, dest_dir: Path, cookies: str | None = None) -> Path` · `fetch_video_360p(url: str, dest_dir: Path, cookies: str | None = None) -> Path` (`cookies` = ชื่อ browser)
  - `class YtDlpClipSource` — opts `quiet`, `no_warnings`, `noprogress`, `js_runtimes={"node": {}}`, `ffmpeg_location=str(find_ffmpeg().parent)`, และ `cookiesfrombrowser=(cookies,)` เมื่อมี · audio format `"ba[ext=m4a]/ba/b"` outtmpl `<dest>/%(id)s.audio.%(ext)s` · video format `"bv*[height<=360]/b[height<=360]/wv*/b"` + `format_sort=["res:360", "+size"]` outtmpl `%(id)s.v360.%(ext)s` · `DownloadError` → `classify_clip_error(str(e), parse_clip_url(url) platform)`
- Produces (`tests/fakes.py`): `FixtureClipSource(root, aliases: dict[str, str] = {}, needs_login: set[str] = set(), cookie_ok: set[str] = set(), unavailable: set[str] = set(), blocked: set[str] = set())` — หา fixture จาก `parse_clip_url(url)` หรือ `aliases[url]` (ค่า = Clip Key); URL ที่หาไม่เจอ → `Unavailable("unsupported")`; key ใน `needs_login` → `NeedsLogin` ถ้า `cookies not in cookie_ok`; บันทึก `info_calls: list[tuple[str, str | None]]` (url, cookies); `fetch_audio` เขียนไฟล์ชื่อ `<key>.audio.m4a`

- [ ] **Step 1: สร้าง fixtures** — สคริปต์ใน scratchpad ใช้ `yt_dlp.YoutubeDL({"quiet": True, "js_runtimes": {"node": {}}}).extract_info(url, download=False)` กับ 3 URL ใน `docs/research/0003-mini-prototype.md` แล้วเก็บเฉพาะ key: `id, extractor_key, title, description, uploader, uploader_id, channel, channel_id, upload_date, timestamp, duration, webpage_url, language, automatic_captions (เก็บแค่ชื่อ key, ค่าเป็น []), subtitles (เช่นกัน), height, width, availability, live_status, age_limit` → JSON UTF-8 indent 1
- [ ] **Step 2: failing tests** (`test_clipsource.py`)
  - `test_parse_youtube_variants`: `watch?v=3xU050kMbHM&t=5`, `https://youtu.be/3xU050kMbHM?si=abc`, `/shorts/3xU050kMbHM`, `https://m.youtube.com/watch?v=3xU050kMbHM` → ทั้งหมด `ClipKey("youtube", "3xU050kMbHM")`
  - `test_parse_tiktok`: `https://www.tiktok.com/@garyvee/video/7479505763950611758?lang=en` → `ClipKey("tiktok", "7479505763950611758")` · `https://vm.tiktok.com/ZMabc123/` → `None`
  - `test_parse_instagram`: `/reels/DejxHqIpgBG/`, `/reel/DejxHqIpgBG/?igsh=x`, `/p/DejxHqIpgBG/` → `ClipKey("instagram", "DejxHqIpgBG")`
  - `test_parse_other_is_none`: `https://www.facebook.com/watch/?v=123` → `None`
  - `test_info_tiktok`: fixture → `key.platform == "tiktok"`, `kind == "short"`, `lang is None`, `creator` ไม่ว่าง
  - `test_info_instagram_title_from_caption`: fixture → `not title.startswith("Video by ")`, `duration == 0` เมื่อ fixture `duration` เป็น null
  - `test_info_youtube_lang_and_kind`: fixture → `lang == "en"`, `kind == "long"`, `duration == 1190`
  - `test_info_unsupported_extractor`: dict `extractor_key="Facebook"` → `Unavailable` reason `"unsupported"`
  - `test_ig_login_error_classified`: `"Requested content is not available, rate-limit reached or login required"` กับ `"instagram"` → `NeedsLogin` · ข้อความเดียวกันกับ `"youtube"` → `Unavailable`
  - `@pytest.mark.network test_real_tiktok_and_youtube_info`: `YtDlpClipSource().fetch_info(...)` สอง URL → key ตรงกับ `parse_clip_url`
- [ ] **Step 3:** run → FAIL
- [ ] **Step 4:** implement `clipsource.py`, เพิ่ม `"unsupported"` ใน `UnavailableReason`, เพิ่ม `FixtureClipSource`
- [ ] **Step 5:** run เทสทั้งหมด → PASS · `-m network -k real_tiktok` → PASS
- [ ] **Step 6: commit** `feat(mini): ClipSource seam for YouTube, TikTok and Instagram URLs`

### Task 4: ClipLibrary — ไฟล์, ชื่อ, index, config, copy เข้า Advisor

**Files:**
- Create: `src/brainsuck/library.py`
- Modify: `src/brainsuck/store.py` (เปลี่ยนชื่อ `_atomic_write` → `atomic_write` และแก้ที่เรียก)
- Test: `tests/test_library.py`

**Interfaces:**
- Consumes: `VideoRecord` clip fields (Task 1) · `render_record`, `parse_record` · `atomic_write` · `MARKER` (advisor.py)
- Produces (`library.py`):
  - `DEFAULT_LIBRARY = Path.home() / "OneDrive" / "Desktop" / "mini-brain"`
  - `clip_key_of(r: VideoRecord) -> str` = `f"{r.platform}_{r.id}"`
  - `slugify(name: str, max_len: int = 60) -> str` — อักขระ `<>:"/\|?*` และ control → ช่องว่าง · ช่องว่างต่อกัน → `-` · ยุบ `-` ซ้ำ · ตัดที่ `max_len` · strip `-. ` หัวท้าย · ไทย/emoji คงไว้
  - `clip_filename(r: VideoRecord) -> str` = `key + (f"__{slug}" if display_name and slug else "") + ".md"`
  - `@dataclass(frozen=True) LibraryConfig(ig_cookies: Literal["ask", "always"] = "ask", browser: str | None = None)`
  - `class ClipLibrary(root: Path)`: attrs `root`, `clips_dir = root / "clips"`
    - `load_config() -> LibraryConfig` (ไม่มี `config.json` → ค่าเริ่มต้น) · `save_config(c: LibraryConfig) -> None`
    - `path_of(key: str) -> Path | None` — ไฟล์ใน `clips/` ที่ `stem == key` หรือ `stem.startswith(key + "__")` **และ** front-matter `platform`+`id` ตรงกับ key
    - `read(key: str) -> VideoRecord | None`
    - `iter_records() -> Iterator[tuple[Path, VideoRecord]]`
    - `write(r: VideoRecord) -> Path` — เขียน `clips/<clip_filename(r)>` แบบ atomic · ลบไฟล์ชื่อเก่าของ key เดียวกัน · ถ้า `summary_status == "done"` และมี `display_name`: เขียนสำเนาเดียวกันไป `<advisor>/clips/<filename>` ของทุก `copied_to` ที่โฟลเดอร์ยังอยู่ (ลบชื่อเก่าใน Advisor ด้วย; Advisor ที่หายไป → ข้าม) · แล้ว `write_index()`
    - `write_index() -> None` — `index.md`: `# Clip Library`, บรรทัดว่าง, หัวตาราง `| ชื่อ | แพลตฟอร์ม | ผู้สร้าง | วันที่ | แท็ก | ไฟล์ |` · ใหม่→เก่าตาม `published` · ชื่อ = `display_name` หรือ title + ` (รอสรุป)` ถ้า pending · แท็ก = `topics` คั่น `, ` · ไฟล์ = `[<filename>](clips/<filename>)` · escape `|`
  - `library_status(lib: ClipLibrary) -> dict` → `{"library": str(root.resolve()), "config": asdict(config), "clips": n, "pending": [absolute paths ที่ summary pending], "unnamed": [keys ที่ done แต่ไม่มี display_name]}`

- [ ] **Step 1: failing tests** (`test_library.py`, record สร้างด้วย `make_record(platform=…)`)
  - `test_slugify_rules`: `"How to Launch: YC/Kat?"` → `"How-to-Launch-YC-Kat"` · `"ขายของ ให้คนรวย 💰"` → `"ขายของ-ให้คนรวย-💰"` · `"a" * 100` → ยาว 60 · `"???"` → `""`
  - `test_filename_unnamed_and_named`: `youtube_3xU050kMbHM.md` → ตั้ง `display_name="How to Launch"` → `youtube_3xU050kMbHM__How-to-Launch.md`
  - `test_rename_removes_old_file`: write ไม่มีชื่อ แล้ว write มีชื่อ → ใน `clips/` เหลือ 1 ไฟล์
  - `test_same_name_two_clips`: สองคลิปคนละ key ชื่อเหมือนกัน → 2 ไฟล์ อ่านกลับได้ถูกตัว
  - `test_path_of_ignores_lookalike_ids`: มี `instagram_Dej` และ `instagram_Dej__x` (id `"Dej__x"`, ไม่มีชื่อ) → `path_of("instagram_Dej")` ได้ไฟล์ของ id `"Dej"` · `read("instagram_Dej__x").id == "Dej__x"`
  - `test_copies_only_when_done_and_named`: `copied_to=[advisor]` (โฟลเดอร์มีอยู่) · pending → ไม่มี `<advisor>/clips/` · done+named → สำเนาเนื้อหาเท่ากับไฟล์ในคลัง · เปลี่ยนชื่อ → สำเนาชื่อเก่าหาย
  - `test_copy_skips_missing_advisor`: `copied_to=[tmp_path / "หายไปแล้ว"]` done+named → write ไม่ error ไม่สร้างโฟลเดอร์นั้น
  - `test_index_rows`: 2 record (หนึ่ง pending, หนึ่ง named มี `|` ในชื่อ) → หัวตารางตรงตัว, ลิงก์ `clips/…`, `\|`, `(รอสรุป)`
  - `test_config_defaults_and_save`: ไม่มีไฟล์ → `LibraryConfig("ask", None)` · save `("always", "firefox")` → load ได้เท่ากัน
  - `test_status_pending_and_unnamed`
- [ ] **Step 2:** run → FAIL
- [ ] **Step 3:** implement `library.py` + rename `atomic_write` ใน `store.py`
- [ ] **Step 4:** run เทสทั้งหมด → PASS
- [ ] **Step 5: commit** `feat(mini): ClipLibrary with naming, index, config and advisor copies`

### Task 5: Clip pipeline — `clip()` และ `import_text()`

**Files:**
- Create: `src/brainsuck/clip.py`
- Test: `tests/test_clip.py`

**Interfaces:**
- Consumes: `ClipSource`, `ClipInfo`, `ClipKey`, `parse_clip_url`, `NeedsLogin` (Task 3) · `ClipLibrary`, `LibraryConfig`, `clip_key_of` (Task 4) · `Transcriber.transcribe_clip`, `whisper_prompt`, `format_lines`, `transcript_quality`, `WHISPER` (Task 2) · `extract_scene_frames` (frames.py, import ระดับ module เพื่อ monkeypatch) · `Blocked`, `Unavailable`, `YouTubeError`
- Produces (`clip.py`):
  - `BROWSERS = ("edge", "firefox", "chrome")`
  - `@dataclass(frozen=True) ClipResult(new: int, existing: int, refreshed: int, skipped: int, needs_login: int, blocked: bool)`
  - `clip(urls: list[str], library: ClipLibrary, *, source: ClipSource, make_transcriber: Callable[[], Transcriber], cache_dir: Path, visual: bool = True, refresh: bool = False, ig_cookies: str | None = None, remember: bool = False, to: list[Path] = (), emit: Callable[[dict], None] = lambda e: None) -> ClipResult`
  - `import_text(library: ClipLibrary, *, url: str, text: str, title: str = "", creator: str = "", to: list[Path] = ()) -> Path`

พฤติกรรมของ `clip()` ต่อ URL (ตามลำดับ, URL ซ้ำในรายการตัดออกก่อนเริ่มโดยดูจาก Clip Key ถ้า parse ได้ ไม่งั้นดูจาก URL):
1. `parse_clip_url` ได้ key และคลังมี record แล้ว และไม่ `refresh` → เพิ่ม `to` เข้า `copied_to` (ไม่ซ้ำ, `str(p.resolve())`) แล้ว `library.write` → event `clip` status `"existing"` · **ไม่เรียก source/Whisper**
2. ไม่งั้น `fetch_info(url)` ไม่ใช้ cookies · ได้ `NeedsLogin` และเป็น instagram → ลอง browser: `[ig_cookies]` ถ้าเป็นชื่อ browser, `BROWSERS` ถ้า `"auto"`, `[config.browser]` ถ้า config `always` · ตัวแรกที่ผ่านคือ browser ของคลิปนี้ (ใช้ต่อกับ audio/video) · ผ่านและ `remember` → `save_config(LibraryConfig("always", browser))` · ไม่มีตัวไหนผ่าน/ไม่มี browser ให้ลอง → event `needs-login` แล้วไปคลิปถัดไป
3. ได้ info แล้ว ถ้า key นี้มีในคลังและไม่ `refresh` → เหมือนข้อ 1 (กรณีลิงก์สั้น)
4. สร้าง record: `transcribe_clip(fetch_audio(...), info.lang, whisper_prompt(info.title, info.creator, info.description))` · segments ว่าง → skipped `"no-speech"` · `visual` → `fetch_video_360p` → `extract_scene_frames(video, cache_dir/"frames"/key, threshold=0.3, max_frames=40)` → rename แต่ละเฟรมเป็น `t{int(sec):05d}.jpg` · `VideoRecord(id=info.key.id, channel_id="", title, kind, published, duration=info.duration or int(segments[-1].start), url=info.url, lang=<ภาษาที่ตรวจได้>, transcript_source=WHISPER, status="active", summary_status="pending", topics=[], screen_frames=[...], summary_md="(pending)", description, transcript_lines=format_lines(segments), platform, display_name=None, creator, transcript_quality=transcript_quality(lines), copied_to=<to>)` · `refresh` ของ record เดิม: คง `display_name` และรวม `copied_to` เดิม
5. ไฟล์งานอยู่ที่ `cache_dir/"work"/key` ลบเสมอ (finally) · Whisper สร้างครั้งเดียวต่อการรัน (lazy)
6. `Unavailable` → skipped `{reason}` · `YouTubeError` อื่น → skipped `"error: <ข้อความ 200 ตัวแรก>"` · `Blocked` → event `blocked` แล้วหยุดทั้งชุด

Events (dict): `{"event":"start","total":n}` · `{"event":"clip","key","path","status":"new"|"existing"|"refreshed","i","n","cookies":<browser|None>}` · `{"event":"skipped","url","reason"}` · `{"event":"needs-login","url","key","tried":[browsers]}` · `{"event":"blocked","message"}` · `{"event":"done", **ClipResult}`

`import_text`: key จาก `parse_clip_url(url)` (ไม่ได้ → `ValueError`) · ย่อหน้าที่ไม่ว่างของ `text` → บรรทัด `[00:00] <ย่อหน้า>` · `transcript_source="nexlev-description"`, `kind="short"`, `published=date.today()`, `lang="th"` ถ้า text มีอักษรไทย ไม่งั้น `"en"`, `summary_status="pending"`, `copied_to=to` → `library.write`

- [ ] **Step 1: failing tests** (`test_clip.py`; fixture `env` คืน `library`, `FakeTranscriber`, `events`, `run(urls, source=None, **kw)` ที่ใช้ `FixtureClipSource(FIX/"clips")` เป็นค่าเริ่มต้นและ `visual=False` เป็นค่าเริ่มต้นของเทส)
  - `test_new_clips_written_pending`: 3 URL → 3 ไฟล์ใน `clips/`, ทุก record `summary_status == "pending"`, `display_name is None`, platform ถูก · events แรก `{"event":"start","total":3}` สุดท้าย `done` · `index.md` มี 3 แถว
  - `test_whisper_gets_prompt_and_lang`: YouTube → `last_lang == "en"`, `last_prompt` มี title · TikTok → `last_lang is None` และ record `lang == "en"` (ค่า `detected`)
  - `test_duplicate_url_reuses_record`: รันซ้ำด้วย `youtu.be/3xU050kMbHM?si=x` → status `"existing"`, `tr.calls` ไม่เพิ่ม, `info_calls` ไม่เพิ่ม
  - `test_short_link_dedup_after_info`: `aliases={"https://vm.tiktok.com/ZMabc/": "tiktok_7479505763950611758"}` หลังมี record แล้ว → status `"existing"`, `tr.calls` ไม่เพิ่ม
  - `test_same_url_twice_in_one_command`: URL เดิม 2 ครั้ง → `start.total == 1`, record เดียว
  - `test_refresh_keeps_name_and_copies`: record named+done+`copied_to` → `refresh=True` → status `"refreshed"`, `summary_status == "pending"`, `display_name` และ `copied_to` เดิม
  - `test_visual_frames_renamed_by_time`: monkeypatch `clip_module.extract_scene_frames` ให้สร้าง `f00001.jpg` คืน `[(12.6, path)]` → `screen_frames == [str(cache/"frames"/key/"t00012.jpg")]` และไฟล์นั้นมีอยู่
  - `test_unclear_lines_set_quality`: `low_conf_files={"tiktok_7479505763950611758.audio.m4a"}` → record `transcript_quality == 0.5` และบรรทัดที่สองลงท้าย `⟨ถอดไม่ชัด⟩`
  - `test_duration_falls_back_to_segments`: IG fixture (duration null) → `duration == 40`
  - `test_ig_needs_login_event`: `needs_login={"instagram_DejxHqIpgBG"}` ไม่มี cookies → event `needs-login` `tried == []`, `needs_login == 1`, ไม่มีไฟล์ IG
  - `test_ig_cookies_auto_order_and_remember`: `cookie_ok={"firefox"}`, `ig_cookies="auto"`, `remember=True` → `info_calls` ของ IG = `[(url, None), (url, "edge"), (url, "firefox")]` · record สร้าง · `load_config() == LibraryConfig("always", "firefox")`
  - `test_config_always_uses_saved_browser`: config `("always","firefox")` ไม่ส่ง `ig_cookies` → ผ่านด้วย firefox
  - `test_cookies_never_for_youtube`: YouTube ใน `needs_login`, `ig_cookies="auto"` → ไม่มี call ที่ cookies ไม่ใช่ `None` สำหรับ URL YouTube, ผลเป็น skipped
  - `test_bad_url_skipped_others_continue`: `["https://www.facebook.com/watch/?v=1", <tiktok>]` → skipped reason `"unsupported"`, tiktok ได้ record
  - `test_blocked_stops_batch`: `blocked={"tiktok_…"}` เป็น URL ที่ 2 จาก 3 → `blocked is True`, record ของ URL แรกอยู่, URL ที่ 3 ไม่ถูกเรียก
  - `test_no_speech_skipped`: `empty_files={…}` → skipped `"no-speech"`
  - `test_to_existing_named_clip_copies_now`: record done+named แล้วรัน URL เดิมด้วย `to=[advisor]` → `<advisor>/clips/<filename>` มีอยู่
  - `test_import_text_creates_record`: text ไทย 2 ย่อหน้า → `transcript_lines == ["[00:00] ย่อหน้า1", "[00:00] ย่อหน้า2"]`, `transcript_source == "nexlev-description"`, `lang == "th"`
- [ ] **Step 2:** run → FAIL
- [ ] **Step 3:** implement `clip.py`
- [ ] **Step 4:** run เทสทั้งหมด → PASS
- [ ] **Step 5: commit** `feat(mini): clip pipeline with dedup, IG cookies fallback and text import`

### Task 6: CLI — `clip`, `clip-name`, `clip-import`, `clip-status`

**Files:**
- Modify: `src/brainsuck/cli.py`, `cli/pyproject.toml` (version `0.2.0`), `tests/test_cli_smoke.py` (`0.2.0`)
- Test: `tests/test_cli_clip.py`

**Interfaces:**
- Consumes: `clip`, `import_text`, `ClipResult` (Task 5) · `ClipLibrary`, `DEFAULT_LIBRARY`, `library_status` (Task 4) · `MARKER` (advisor.py) · `YtDlpClipSource` (Task 3)
- Produces: `main(argv=None, *, yt=None, make_transcriber=None, clip_source=None) -> int` และคำสั่ง (ทุกคำสั่งรับ `--library DIR`, ค่าเริ่มต้น env `BRAINSUCK_LIBRARY` ไม่งั้น `DEFAULT_LIBRARY`; สร้างโฟลเดอร์คลังถ้ายังไม่มี):
  - `clip <url>... [--no-visual] [--refresh] [--to ADVISOR]... [--ig-cookies {auto,edge,firefox,chrome}] [--remember]` → JSON lines (events ของ Task 5) · exit `0` (รวมกรณี skipped/needs-login) · `2` blocked · `3` `--to` ที่ `CLAUDE.md` ไม่มี `MARKER` → `{"event":"error","kind":"not-an-advisor","path":…}` **ก่อนเรียก source** · `1` error อื่น
  - `clip-name <key> <name>` → ตั้ง `display_name`, `library.write` → `{"event":"named","key","path"}` · key ไม่มี → exit 1 `{"event":"error","kind":"unknown-clip","key"}` · ชื่อที่ `slugify` แล้วว่าง → exit 1 `kind: "bad-name"`
  - `clip-import --url URL --text-file FILE [--title T] [--creator C] [--to ADVISOR]...` → `{"event":"clip","key","path","status":"new"}` (อ่านไฟล์ UTF-8)
  - `clip-status` → `library_status(...)` เป็น JSON บรรทัดเดียว

- [ ] **Step 1: failing tests** (`test_cli_clip.py`, ส่ง `clip_source=FixtureClipSource(...)`, `make_transcriber=lambda: FakeTranscriber()`, `--library <tmp>` และ `BRAINSUCK_CACHE=<tmp>/cache` ผ่าน monkeypatch)
  - `test_clip_cmd_streams_json`: exit 0, ทุกบรรทัด stdout เป็น JSON, บรรทัดสุดท้าย `event == "done"`
  - `test_clip_to_non_advisor_exit3`: `--to <tmp>/ไม่ใช่ที่ปรึกษา` → exit 3, `kind == "not-an-advisor"`, `info_calls == []`
  - `test_clip_name_renames`: หลัง clip → `clip-name tiktok_7479505763950611758 "ขายของให้คนรวย"` → exit 0, ไฟล์ `tiktok_7479505763950611758__ขายของให้คนรวย.md`
  - `test_clip_name_unknown_exit1` · `test_clip_name_bad_name_exit1` (`"???"`)
  - `test_clip_import_from_file`: text ไทยในไฟล์ชื่อมีช่องว่าง → exit 0, record `nexlev-description`
  - `test_clip_status_json`: มี `pending` 3 path, `unnamed == []`
  - `test_library_from_env`: ไม่ส่ง `--library`, `BRAINSUCK_LIBRARY=<tmp>/คลัง` → `clip-status` คืน `library` เป็น path นั้น
  - `test_exit_blocked`: → exit 2
- [ ] **Step 2:** run → FAIL
- [ ] **Step 3:** implement ใน `cli.py` (import แบบ lazy เหมือนเดิม; `__version__ = "0.2.0"`) + pyproject `version = "0.2.0"`
- [ ] **Step 4:** run เทสทั้งหมด → PASS
- [ ] **Step 5:** smoke จริง (เน็ต + GPU): `BRAINSUCK_CACHE=C:/brain-sucker-cache/mini BRAINSUCK_LIBRARY="C:/brain-sucker-cache/mini/lib ทดสอบ" bash plugins/brain-sucker/bin/brainsuck clip https://www.tiktok.com/@garyvee/video/7479505763950611758` → event `clip` status `new`, ไฟล์ record มี transcript, `screen_frames` ชี้ไฟล์ `t*.jpg` ที่มีอยู่ (ครั้งแรกติดตั้ง venv นานหลายนาที)
- [ ] **Step 6: commit** `feat(mini): brainsuck clip, clip-name, clip-import and clip-status`

### Task 7: ฝั่ง Claude — skill `mini-brain`, summarizer ทั่วไป, advisor ค้น `clips/`

**Files:**
- Create: `plugins/brain-sucker/skills/mini-brain/SKILL.md`
- Modify: `plugins/brain-sucker/agents/video-summarizer.md`, `plugins/brain-sucker/skills/advisor/SKILL.md`, `plugins/brain-sucker/.claude-plugin/plugin.json` (version `0.2.0`, description เพิ่ม "· /mini-brain เก็บคลิปเดี่ยว YouTube/TikTok/IG เป็นคลังที่ปรึกษาส่วนตัว")

**Interfaces:**
- Consumes: คำสั่ง CLI และ events ของ Task 6 · Video Record clip fields · agent `brain-sucker:video-summarizer`

**`skills/mini-brain/SKILL.md`** — front-matter: `name: mini-brain` · `description: Use when the user pastes YouTube / TikTok / Instagram video URLs to watch, remember or discuss ("/mini-brain <url...>"), or asks a question of their personal clip library ("/mini-brain <คำถาม>").` · `argument-hint: <url...> [--no-visual] [--refresh] [--to <Advisor>] | <คำถาม>` · `allowed-tools: Bash(brainsuck *)`. เนื้อหาต้องมีครบ:
1. **กฎเหล็ก**: ห้ามสร้าง/เขียนไฟล์ในโฟลเดอร์ปัจจุบัน (ไฟล์ชั่วคราวใช้ scratchpad) · ห้ามถามรหัสผ่าน/อีเมล
2. **โหมด URL** (มี URL ใน argument):
   - รัน `brainsuck clip <urls> [flags]` เบื้องหลัง · รายงานความคืบหน้าจาก event `clip` · บอกผู้ใช้ว่าคลิป 10 นาทีใช้ราว 1–1.5 นาที · ครั้งแรกติดตั้งนานหลายนาที · exit 2/3/1 จัดการแบบ skill `brain-suck`
   - `needs-login`: ถามครั้งเดียวต่อชุดด้วย AskUserQuestion "ใช้การล็อกอิน Instagram ที่มีอยู่ใน browser ไหม" ตัวเลือก ใช่ / ไม่ / ใช่ทุกครั้ง · ใช่ → รันซ้ำเฉพาะ URL เหล่านั้นด้วย `--ig-cookies auto` (ใช่ทุกครั้ง → เพิ่ม `--remember`) · ถ้า `tried` ไม่ว่างและยัง `needs-login` หรือผู้ใช้ตอบไม่ → ถาม "ใช้เครดิต NexLev กับ N คลิปไหม" · ใช่ → เรียก `watch_instagram_video_and_ask` ขอคำบรรยายละเอียดทุกช่วง (คำพูด + สิ่งที่เห็นบนจอ) → เขียนผลลง scratchpad → `brainsuck clip-import --url … --text-file …` · ไม่ → รายงานว่าข้าม
   - สรุป: `brainsuck clip-status` → `pending` แบ่ง batch 5 ส่ง `brain-sucker:video-summarizer` พร้อมกันไม่เกิน 8 จนว่าง (batch ที่ failed ลองใหม่ 1 รอบ) · แล้วลบโฟลเดอร์เฟรมของ record ที่สรุปแล้ว
   - ตั้งชื่อ: คลิปใน `unnamed` ที่มาจากชุดนี้ → **ตารางเดียว** `| # | ชื่อที่เสนอ | ชื่อจริง | แพลตฟอร์ม · ผู้สร้าง | ความยาว |` ชื่อที่เสนอเป็นภาษาของผู้ใช้ ≤ 60 ตัว บอกแก่นของคลิป · ผู้ใช้ตอบ `ok` หรือแก้รายข้อ → `brainsuck clip-name <key> "<ชื่อ>"` ทีละคลิป
   - โหลดเข้าแชท: ทุกคลิปในชุด อ่าน front-matter + `## Summary` + `## Screen Text` · อ่าน `## Transcript` ทั้งหมดเฉพาะ `duration ≤ 1800` · ยาวกว่านั้น grep transcript ตามคำถามทีหลัง · บอกผู้ใช้ว่าพร้อมคุย + คลิปที่ `transcript_quality > 0` หรือ `nexlev-description`
3. **โหมดคำถาม** (ไม่มี URL): `brainsuck clip-status` เอา path คลัง → อ่าน `index.md` → grep `clips/*.md` (คำของผู้ใช้ + ภาษาของคลิป) → อ่าน Summary ของที่เจอแล้ว Transcript รอบ timestamp → ตอบตามกฎของ skill `advisor` (Provenance Label สามส่วน) แต่หัวข้อแรกเป็น **จากคลิป**
4. **ไม่มี argument**: บอกจำนวนคลิปและ 10 คลิปล่าสุดจาก `index.md` แล้วถามว่าจะทำอะไร
5. **Citation** (ทั้งในโหมด URL ที่คุยต่อ และโหมดคำถาม): YouTube → `[<display_name> @ mm:ss](https://youtu.be/<id>?t=<วินาที>)` · TikTok/IG → `[<display_name> @ mm:ss](<url>)` · อ้างบรรทัดที่มี `⟨ถอดไม่ชัด⟩` ต้องบอก "(ช่วงนี้ถอดเสียงไม่ชัด)" · record `nexlev-description` ต้องบอก "(จากคำบรรยายของ NexLev ไม่ใช่คำพูดจริง)"

**`agents/video-summarizer.md`** — แก้เฉพาะ:
- ตัวอย่างใน Screen Text: "a recipe card, measurements, a slide, a chart, a price or metric" · ชื่อเฟรม `t<seconds>.jpg` = เวลาของเฟรมนั้น ใช้เป็น timestamp (ชื่อแบบอื่นใช้วิธีเดิม)
- Steps & numbers: "a bullet per concrete step, number, metric, price, ingredient amount, temperature, time, or measurement"
- เพิ่มข้อ: Transcript ที่ถอดด้วย Whisper มักสะกดชื่อคน/บริษัท/ผลิตภัณฑ์ผิด — สะกดตาม `title`, `## Description` และ `creator` เมื่อชัดว่าเป็นคำเดียวกัน · บรรทัดที่ลงท้าย `⟨ถอดไม่ชัด⟩` ถ้าใช้เป็นที่มาของ bullet ให้ต่อท้าย bullet ว่า "(ถอดไม่ชัด)"
- topics: "(subjects, techniques, tools, named people or companies, dishes, ingredients)"
- ห้ามแตะ field `platform`, `display_name`, `creator`, `transcript_quality`, `copied_to` (กฎ "every other front-matter field byte-for-byte" ครอบคลุมอยู่แล้ว — เพิ่มชื่อ field ให้ชัด)

**`skills/advisor/SKILL.md`** — ขั้นที่ 4 ของบันได: "`grep` `clips/*.md` — Clips the user added one by one (no Channel; not in `advisor.md`)" · Citation ของ clip ใช้กฎข้อ 5 ของ mini-brain · Recency Weighting ไม่ใช้กับ clips

- [ ] **Step 1:** เขียน `skills/mini-brain/SKILL.md` ตามรายการข้างบน
- [ ] **Step 2:** แก้ `video-summarizer.md`, `advisor/SKILL.md`, `plugin.json`
- [ ] **Step 3:** `claude plugin validate plugins/brain-sucker` (และ `.` ที่ root ของ worktree) → ไม่มี error
- [ ] **Step 4: ตรวจ summarizer จริง** — ใช้ record TikTok + record YouTube 3xU050kMbHM จากคลังทดสอบ (`C:/brain-sucker-cache/mini/lib ทดสอบ`, สร้างด้วยคำสั่ง Task 6 Step 5 เพิ่ม URL YouTube) ส่ง agent `brain-sucker:video-summarizer` (จาก worktree: copy ข้อความ agent ไปใช้เป็น prompt ของ general-purpose agent model haiku ถ้า plugin ยังชี้ checkout หลัก) → ตรวจ: `summary: done`, ชื่อ "Kat Mañalac" สะกดถูกใน Summary, Screen Text มี timestamp ตรงกับชื่อเฟรม, field clip ไม่เปลี่ยนไบต์ (`git diff --no-index` เทียบ front-matter)
- [ ] **Step 5: ตรวจ v1 ไม่ถดถอย** — ส่ง summarizer ตัวใหม่กับ record อาหาร 1 ไฟล์ จาก `C:\brain-sucker-cache\test-advisor ทดสอบ` (copy ไป scratchpad, reset เป็น pending) → Summary ยังมี Steps & numbers ของสูตร
- [ ] **Step 6: commit** `feat(mini): mini-brain skill, general summarizer, advisor reads clips/`

### Task 8: E2E จริง + เอกสาร + ปิดงาน

**Files:**
- Create: `docs/research/0004-mini-e2e.md`
- Modify: `docs/HANDOFF.md` (§2 สถานะ mini), `.superpowers/sdd/2026-11-08-mini-brain/progress.md` (ledger)

ทดสอบด้วย plugin จาก worktree: `BRAINSUCK_CACHE=C:/brain-sucker-cache/mini claude --plugin-dir "C:/Users/Lenovo/OneDrive/Desktop/brain-sucker-mini/plugins/brain-sucker" -p "…"` · ถ้า plugin `brain-sucker@brain-sucker-local` ที่ติดตั้งไว้ชนชื่อ ให้ `claude plugin disable` ชั่วคราว **เฉพาะตอนที่ v1 E2E ไม่ได้รันอยู่** แล้ว enable คืนทันทีหลังจบ · คลังที่ใช้ = คลังจริง `Desktop\mini-brain` (ผู้ใช้สร้างไว้เพื่อสิ่งนี้)

- [ ] **Step 1: โหมด URL** — สร้างโฟลเดอร์ว่าง `C:\brain-sucker-cache\mini\e2e-สุ่ม 1` · cwd นั้น: `claude -p "/brain-sucker:mini-brain <TikTok> <YouTube 3xU050kMbHM> <IG DejxHqIpgBG>"` → หยุดที่ตารางชื่อ → `claude -c -p "ok"` → ตรวจ: คลังมี 3 record `summary: done` มีชื่อ, `index.md` 3 แถว, โฟลเดอร์เฟรมถูกลบ, **โฟลเดอร์สุ่มยังว่าง**, คำตอบสุดท้ายบอกว่าพร้อมคุย · จับเวลาต่อคลิป
- [ ] **Step 2: คุยต่อในแชทเดิม** — `claude -c -p "Kat แนะนำให้ launch กี่ครั้ง"` → ตอบพร้อม Citation `youtu.be/3xU050kMbHM?t=`
- [ ] **Step 3: โหมดคำถามจากโฟลเดอร์ใหม่** — `C:\brain-sucker-cache\mini\e2e-สุ่ม 2`: คำถามเรื่องคลิป TikTok และคลิป IG ภาษาไทย → Citation ชี้ URL TikTok/IG, ระบุถ้าอ้างช่วง `⟨ถอดไม่ชัด⟩`
- [ ] **Step 4: ซ้ำ + ส่งเข้า Advisor** — `brainsuck clip <YouTube> --to "C:\brain-sucker-cache\test-advisor ทดสอบ"` → status `existing` < 10 วินาที, ไฟล์อยู่ใน `<Advisor>/clips/` · `claude -p` ใน Advisor นั้นถามเรื่องคลิป → skill `advisor` อ้าง clip ได้ · `--to` โฟลเดอร์ที่ไม่ใช่ Advisor → exit 3
- [ ] **Step 5: บันทึก** `docs/research/0004-mini-e2e.md`: เวลาต่อคลิปเทียบเป้า "ไม่กี่นาที", ชื่อเฉพาะที่ Whisper ยังเพี้ยน (ผลของ `initial_prompt`), สัดส่วน `⟨ถอดไม่ชัด⟩` ที่เกณฑ์ -1.0, ทาง IG ล็อกอิน/NexLev ทดสอบจริงหรือแค่ unit test · อัปเดต `docs/HANDOFF.md` · commit `docs: mini brain sucker E2E results`
- [ ] **Step 6: Final review** ตาม `superpowers:executing-plans` § Final Review (review-package ทั้ง branch `feat/mini` เทียบ `feat/v1` + reviewer บน model ที่เก่งสุด) → แก้ตามที่รับ → `superpowers:finishing-a-development-branch` (merge ลำดับ: `feat/v1` เข้า `main` ก่อน แล้วค่อย `feat/mini`)
