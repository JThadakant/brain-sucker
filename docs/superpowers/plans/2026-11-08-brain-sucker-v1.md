# Brain Sucker v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Claude Code plugin ที่รับ Channel Query → Ingest ทั้งช่องเป็น Channel Knowledge ในโฟลเดอร์ Advisor → เปิด Claude ในโฟลเดอร์นั้นแล้วได้ที่ปรึกษาที่ตอบพร้อม Citation

**Architecture:** 2 ซีกแยกกันที่รูปแบบไฟล์: Python CLI `brainsuck` (deterministic: resolve / ingest / status — เขียน Video Records, `index.md`, `state.json`) และฝั่ง Claude (skill `brain-suck` ควบคุม, agents Haiku สรุปรายคลิป, agents Opus สังเคราะห์, skill `advisor` เก็บกฎการตอบ). YouTube และ Transcriber เป็น internal seam ที่มี 2 adapters (จริง + fake)

**Tech Stack:** Python 3.12, yt-dlp (+ejs, Node เป็น JS runtime), faster-whisper large-v3 (CUDA, RTX 4070), ffmpeg 9, PyYAML, pytest · Claude Code plugin (skills, agents, bin/)

**Spec:** `docs/DESIGN.md` (หลัก) · `docs/PLAN.md` · `GLOSSARY.md` · `docs/adr/0001–0005` · `docs/research/0001-tech-facts.md`, `0002-phase1-prototype.md`

## Global Constraints

- Python 3.12 · package `brainsuck` อยู่ที่ `plugins/brain-sucker/cli/src/brainsuck/` · tests ที่ `plugins/brain-sucker/cli/tests/`
- Pins: `yt-dlp[default,curl-cffi]>=2026.10.26` · `av<16` · `nvidia-cublas-cu12==12.9.2.10` · `faster-whisper>=1.2.1` · `pyyaml`
- yt-dlp ทุกคำสั่ง: `js_runtimes` = node · ห้ามใช้ cookies · `--sub-langs` ต้องระบุตรงตัว (`<lang>` และ `<lang>-orig`) **ห้าม `all` หรือ pattern**
- Whisper: `large-v3`, `device="cuda"`, `compute_type="float16"`, `BatchedInferencePipeline(batch_size=8)` · **ห้าม turbo**
- Transcript: ภาษาไทย → Whisper เสมอ · ภาษาอื่น → ซับ manual ภาษาเดียวกัน > `<lang>-orig` auto > Whisper
- Cache root: env `BRAINSUCK_CACHE` ค่าเริ่มต้น `C:\brain-sucker-cache` · venv ที่ `<cache>/venv` · ไฟล์เสียง/วิดีโอลบทันทีหลังใช้
- Live ไม่ Ingest · Video Kind มีแค่ `long` / `short`
- ไฟล์ทุกไฟล์ UTF-8 · stdout ของ CLI ต้อง UTF-8 (`sys.stdout.reconfigure(encoding="utf-8")`) · JSON `ensure_ascii=False`
- path ทุกที่ต้องรองรับช่องว่างและอักษรไทย (`brain sucker`, `ที่ปรึกษาทำอาหาร`)
- ศัพท์ในโค้ด/ไฟล์ตรงกับ `GLOSSARY.md` (Advisor, Channel, Video, Video Record, Ingest, Skipped Video, Removed Video …)

## Review Focus

1. **Ingest ถูกขัดจังหวะกลางคลิป** (Ctrl+C, ไฟดับ) → รันซ้ำแล้วทำต่อ ไม่มี Video Record ครึ่งไฟล์ ไม่มีซ้ำ → Task 5 (atomic write) + Task 8
2. **listing ผิดปกติ** (yt-dlp คืนรายการว่าง/หายเกินครึ่ง) → ต้องไม่ mark Video ทั้งช่องเป็น Removed → Task 4
3. **YouTube บล็อกกลางทาง** (429 / "confirm you're not a bot") → หยุดอย่างสุภาพ, state บันทึกแล้ว, exit code 2, ไม่ลงเป็น Skipped Video → Task 8
4. **โฟลเดอร์ Advisor ชื่อไทย + มีช่องว่าง, handle ไม่ใช่ ASCII** → ทำงานได้ ชื่อโฟลเดอร์ Channel ปลอดภัยบน Windows → Task 8 + Task 9
5. **ช่องอังกฤษแต่คลิปไม่มีซับเลย** → ใช้ Whisper ไม่ใช่ข้าม · **metadata refresh** ต้องไม่ลบ `## Summary` ที่สรุปแล้ว → Task 3 + Task 2

---

### Task 1: Repo, marketplace, plugin และ package โครง

**Files:**
- Create: `.gitignore` (`__pycache__/`, `.pytest_cache/`, `*.egg-info/`)
- Create: `.claude-plugin/marketplace.json` → `{"name":"brain-sucker-local","owner":{"name":"Jiradech"},"plugins":[{"name":"brain-sucker","source":"./plugins/brain-sucker"}]}`
- Create: `plugins/brain-sucker/.claude-plugin/plugin.json` → `{"name":"brain-sucker","version":"0.1.0","description":"ดูดช่อง YouTube ทั้งช่องให้โฟลเดอร์กลายเป็นที่ปรึกษา"}`
- Create: `plugins/brain-sucker/cli/pyproject.toml` (deps ตาม Global Constraints; extras `asr` = faster-whisper, av, nvidia-cublas-cu12; `dev` = pytest; script `brainsuck = "brainsuck.cli:main"`; pytest markers `network`, `gpu`)
- Create: `plugins/brain-sucker/cli/src/brainsuck/__init__.py`, `__main__.py`, `cli.py`
- Test: `plugins/brain-sucker/cli/tests/test_cli_smoke.py`

**Interfaces:**
- Produces: `brainsuck.cli.main(argv: list[str] | None = None) -> int` (subcommands ว่างไว้ก่อน; `--version` พิมพ์ `0.1.0`)

- [ ] **Step 1:** `git init` ที่ root, ตั้ง branch `main`, commit เอกสารที่มีอยู่ (`docs/`, `GLOSSARY.md`) — แล้วสร้าง branch `prototype/phase1` ที่มีเฉพาะ `prototypes/phase1/` commit ไว้ (ตามกติกา prototype) และลบ `prototypes/` ออกจาก `main`
- [ ] **Step 2: failing test** `test_version_prints`: `main(["--version"])` คืน 0 และ stdout มี `0.1.0`
- [ ] **Step 3:** run `pytest -q` (ใน venv ทดสอบ `C:\brain-sucker-cache\venv-dev`, `pip install -e "plugins/brain-sucker/cli[dev]"`) → FAIL
- [ ] **Step 4:** implement `main` ด้วย `argparse` + `sys.stdout.reconfigure(encoding="utf-8")`
- [ ] **Step 5:** `pytest -q` → PASS · `claude plugin validate .` → ไม่มี error
- [ ] **Step 6:** commit `chore: scaffold marketplace, plugin and brainsuck package`

### Task 2: Domain types + Record codec

**Files:**
- Create: `src/brainsuck/models.py`, `src/brainsuck/record.py`
- Test: `tests/test_record.py`

**Interfaces:**
- Produces (`models.py`, dataclasses):
  - `Segment(start: float, text: str)`
  - `VideoRef(id: str, title: str, kind: Literal["long","short"])`
  - `VideoInfo(id, channel_id, title, description, published: date, duration: int, kind, url, lang: str, captions: dict[str, Literal["manual","auto"]])`
  - `VideoRecord(id, channel_id, title, kind, published: date, duration: int, url, lang, transcript_source: Literal["youtube-manual","youtube-auto","whisper-large-v3"], status: Literal["active","removed"], summary_status: Literal["pending","done"], topics: list[str], screen_frames: list[str], summary_md: str, description: str, transcript_lines: list[str])`
- Produces (`record.py`):
  - `record_filename(r: VideoRecord) -> str` → `"YYYY-MM-DD_<id>.md"`
  - `render_record(r: VideoRecord) -> str` · `parse_record(text: str) -> VideoRecord`
  - `refresh_metadata(r: VideoRecord, info: VideoInfo) -> VideoRecord` (แทน title/description/duration เท่านั้น)
  - `mark_removed(r: VideoRecord) -> VideoRecord`

รูปแบบไฟล์ตรงตาม `docs/DESIGN.md` § รูปแบบ Video Record (front-matter YAML: `summary` คือ `summary_status`; sections `## Summary`, `## Description`, `## Transcript`, และ `## Screen Text` เมื่อมี). Record ใหม่มี `summary_md = "(pending)"`

- [ ] **Step 1: failing tests**
  - `test_round_trip`: `parse_record(render_record(r)) == r` สำหรับ record ภาษาไทยที่ title มี `:` และ `"`
  - `test_filename`: published `2026-10-01`, id `K_SXQoMdSf4` → `"2026-10-01_K_SXQoMdSf4.md"`
  - `test_refresh_keeps_summary`: record ที่ `summary_status="done"`, `summary_md="สรุปเดิม"`, `topics=["stew"]` → หลัง `refresh_metadata` ด้วย title ใหม่ → title เปลี่ยน, summary_md/topics/transcript_lines/summary_status เดิม
  - `test_mark_removed`: status → `"removed"`, ส่วนอื่นไม่เปลี่ยน
- [ ] **Step 2:** `pytest tests/test_record.py -q` → FAIL
- [ ] **Step 3:** implement — `yaml.safe_dump(..., allow_unicode=True, sort_keys=False)`; แยก section ด้วยหัวข้อ `## ` ระดับ 2 เท่านั้น
- [ ] **Step 4:** → PASS · commit `feat: video record codec`

### Task 3: Transcript policy + caption parsing + formatting

**Files:**
- Create: `src/brainsuck/transcript.py`
- Test: `tests/test_transcript.py`, fixtures `tests/fixtures/captions/*.json3` (ตัดสั้นจาก `C:\brain-sucker-cache\proto\out\*\*.json3` ≤ 20 events)

**Interfaces:**
- Produces:
  - `detect_lang(info_json: dict) -> str` — `info_json["language"]` ถ้ามี ไม่งั้นเอาจาก key ใน `automatic_captions` ที่ลงท้าย `-orig` (ตัด `-orig`) ไม่งั้น `"en"`
  - `choose_source(lang: str, captions: dict[str, str]) -> tuple[str, str | None]` → (`transcript_source`, caption key หรือ `None` ถ้า Whisper)
  - `parse_json3(data: dict) -> list[Segment]` (ตัด `[music]`/`[Music]`/`>>`, รวมช่องว่าง)
  - `format_lines(segments: list[Segment], window: float = 30.0) -> list[str]` → บรรทัดละ `"[mm:ss] ..."` (≥1 ชม. ใช้ `"[h:mm:ss]"`) ขึ้นบรรทัดใหม่เมื่อ segment เริ่ม ≥ `window` วินาทีหลังต้นบรรทัด

- [ ] **Step 1: failing tests**
  - `test_thai_always_whisper`: `choose_source("th", {"th":"auto","th-orig":"auto"}) == ("whisper-large-v3", None)`
  - `test_manual_beats_auto`: `choose_source("en", {"en":"manual","en-orig":"auto"}) == ("youtube-manual","en")`
  - `test_orig_auto`: `choose_source("en", {"en-orig":"auto","en":"auto"}) == ("youtube-auto","en-orig")`
  - `test_no_captions_falls_back_to_whisper`: `choose_source("en", {}) == ("whisper-large-v3", None)`
  - `test_parse_json3_strips_music`: fixture Chocolate → ไม่มี `[music]` ในข้อความ, `segments[0].start == 0.0`-ish (`< 1`)
  - `test_format_lines`: segments ที่ 0, 12, 31, 3700 วินาที → `["[00:00] a b", "[00:31] c", "[1:01:40] d"]`
  - `test_detect_lang_from_orig`: `{"automatic_captions":{"th-orig":[],"en":[]}}` → `"th"`
- [ ] **Step 2:** → FAIL · **Step 3:** implement · **Step 4:** → PASS · commit `feat: transcript source policy and formatting`

### Task 4: Sync planner

**Files:**
- Create: `src/brainsuck/sync.py`
- Test: `tests/test_sync.py`

**Interfaces:**
- Consumes: `VideoRef`
- Produces:
  - `KnownVideo(id: str, title: str, status: Literal["active","removed"])`
  - `SyncPlan(new: list[str], refresh: list[str], removed: list[str], restored: list[str])`
  - `plan_sync(remote: list[VideoRef], known: dict[str, KnownVideo], skipped: set[str]) -> SyncPlan` — `new` เรียงตามลำดับ `remote` (ใหม่→เก่า, Long ก่อนเมื่อผู้เรียกส่ง Long list ก่อน) ไม่รวม id ใน `skipped`; `refresh` = title เปลี่ยน; `removed` = active ที่ไม่อยู่ใน remote; `restored` = removed ที่กลับมา
  - `class SuspiciousListing(Exception)` — raise เมื่อ `remote` ว่างแต่ `known` มี active, หรือ active ที่หายไป > 50% และ > 5 รายการ

- [ ] **Step 1: failing tests** — `test_new_in_remote_order`, `test_skipped_not_new`, `test_title_change_is_refresh`, `test_missing_is_removed`, `test_removed_back_is_restored`, `test_empty_listing_raises` (`known` มี 3 active, remote `[]` → `SuspiciousListing`), `test_mass_disappearance_raises` (20 active, remote เหลือ 8 → raise), `test_small_drop_ok` (20 → 18 → removed 2 รายการ)
- [ ] **Step 2:** → FAIL · **Step 3:** implement · **Step 4:** → PASS · commit `feat: incremental sync planner`

### Task 5: Channel store (state, index, skipped, atomic write)

**Files:**
- Create: `src/brainsuck/store.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Consumes: `VideoRecord`, `render_record`, `parse_record`, `record_filename`, `KnownVideo`
- Produces: `class ChannelStore`:
  - `ChannelStore(channel_dir: Path)` · `channel_dir` = `<advisor>/channels/<folder>/`
  - `load_state() -> ChannelState` · `save_state(s: ChannelState) -> None`
  - `ChannelState(channel_id: str, handle: str | None, folder: str, title: str, known: dict[str, KnownVideo], skipped: dict[str, str])` (skipped: id → เหตุผล)
  - `write_record(r: VideoRecord) -> Path` · `read_record(video_id: str) -> VideoRecord | None` · `iter_records() -> Iterator[VideoRecord]`
  - `write_index() -> None` → `index.md`: ตาราง `| วันที่ | ประเภท | ชื่อ | สรุปแล้ว | ไฟล์ |` เรียงใหม่→เก่า, Removed Video มี ` (ลบแล้ว)` ต่อท้ายชื่อ
  - `write_skipped() -> None` → `skipped.md` (id, เหตุผล, ลิงก์)
- ทุกการเขียนไฟล์ใช้ `_atomic_write(path, text)`: เขียน `path.with_suffix(".tmp")` แล้ว `os.replace`

- [ ] **Step 1: failing tests** (ใช้ `tmp_path` ชื่อ `"ที่ปรึกษา ทดสอบ"`) — `test_state_round_trip`, `test_write_then_read_record`, `test_index_order_and_removed_label`, `test_no_tmp_left_after_write`, `test_leftover_tmp_ignored_by_iter_records` (มี `x.tmp` ค้างใน videos/ → `iter_records` ไม่อ่าน)
- [ ] **Step 2:** → FAIL · **Step 3:** implement · **Step 4:** → PASS · commit `feat: channel store with atomic writes`

### Task 6: YouTube seam — `FixtureYouTube` + `YtDlpYouTube`

**Files:**
- Create: `src/brainsuck/youtube.py`
- Test: `tests/test_youtube.py`, fixtures `tests/fixtures/youtube/` (info.json ตัด field ใหญ่ออก 4 คลิปจาก prototype + listing JSON)

**Interfaces:**
- Produces:
  - `ChannelCandidate(channel_id: str, title: str, handle: str | None, subscribers: int | None, video_count: int | None)`
  - `class YouTube(Protocol)`: `resolve(query: str) -> list[ChannelCandidate]` · `list_channel(channel_id: str) -> tuple[ChannelCandidate, list[VideoRef]]` (Long ก่อน แล้ว Short; แต่ละกลุ่มใหม่→เก่า) · `fetch_info(video_id: str) -> VideoInfo` · `fetch_captions(video_id: str, key: str) -> list[Segment]` · `fetch_audio(video_id: str, dest_dir: Path) -> Path` · `fetch_video_360p(video_id: str, dest_dir: Path) -> Path`
  - `class Blocked(Exception)` — HTTP 429 หรือข้อความ "Sign in to confirm" · `class Unavailable(Exception)` มี `reason: Literal["members-only","age-restricted","private","live","unavailable"]`
  - `FixtureYouTube(root: Path, blocked_after: int | None = None)` — `blocked_after=n` ทำให้ `fetch_info` ครั้งที่ n+1 raise `Blocked`
  - `YtDlpYouTube(sleep_requests: float = 1.0)` — ใช้ `yt_dlp.YoutubeDL` API (ไม่ใช่ subprocess) ด้วย options: `js_runtimes={"node":{}}`, `extractor_args={"youtubetab":{"approximate_date":[""]}}` สำหรับ listing, `skip_download` + `writesubtitles`/`writeautomaticsub` + `subtitleslangs=[key]` + `subtitlesformat="json3"` สำหรับซับ, format `"ba[ext=m4a]/ba"` เสียง, `"bv*[height<=360]/b[height<=360]/wv*"` + `format_sort=["res:360","+size"]` วิดีโอ · `kind` = `"short"` ถ้ามาจากแท็บ `/shorts` · `live_status` ที่ไม่ใช่ `not_live`/`None` → `Unavailable("live")`
  - `resolve`: `@handle`/URL → ดึง channel ตรง (1 รายการ) · ข้อความ → `ytsearch10:` แล้วรวมตาม channel_id เอา 3 อันดับแรก

- [ ] **Step 1: failing tests (fixture)** — `test_fixture_lists_long_then_short`, `test_fixture_info_maps_fields` (K_SXQoMdSf4: duration 368, kind long, captions มี `"en":"manual"`), `test_fixture_blocked_after`
- [ ] **Step 2: network smoke tests** (`@pytest.mark.network`): `test_ytdlp_list_nicks_kitchen` (≥ 80 long, ≥ 90 short), `test_ytdlp_resolve_handle_and_text` ("Nick's Kitchen" → candidate แรก `UC2HNqPgeKtVr2gZmLeeIk3g`), `test_ytdlp_captions_k_sxq` (segments > 20)
- [ ] **Step 3:** → FAIL · **Step 4:** implement · **Step 5:** `pytest -q` (fixture) และ `pytest -q -m network` → PASS · commit `feat: youtube seam with yt-dlp and fixture adapters`

### Task 7: Transcriber seam + scene frames

**Files:**
- Create: `src/brainsuck/transcribe.py`, `src/brainsuck/frames.py`
- Test: `tests/test_transcribe.py`, `tests/test_frames.py`

**Interfaces:**
- Produces:
  - `class Transcriber(Protocol)`: `transcribe(audio: Path, lang: str) -> list[Segment]`
  - `FakeTranscriber(text_by_file: dict[str, str] | None = None)` — คืน 1 segment ต่อไฟล์ และนับจำนวนครั้งที่ถูกเรียก (`calls: int`)
  - `FasterWhisperTranscriber()` — ตอน construct: หา `nvidia/cublas/bin` ใน `nvidia.cublas.__path__` แล้ว `os.add_dll_directory` + ต่อหน้า `PATH` ก่อน import `faster_whisper`; โหลดโมเดลครั้งเดียว
  - `find_ffmpeg() -> Path` — `shutil.which("ffmpeg")` ไม่งั้นค้นใน `%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_*\ffmpeg-*\bin\ffmpeg.exe`
  - `extract_scene_frames(video: Path, out_dir: Path, threshold: float = 0.4, max_frames: int = 40) -> list[tuple[float, Path]]` — `select='gt(scene,T)',showinfo` + `-fps_mode vfr`, เวลาจาก `pts_time`, ถ้าเกิน `max_frames` เลือกกระจายเท่าๆ กัน

- [ ] **Step 1: failing tests** — `test_fake_transcriber_counts`; `test_find_ffmpeg_exists`; `@pytest.mark.gpu test_whisper_short_clip` (ข้ามถ้าไม่มี `C:\brain-sucker-cache\proto\out\nick-short-chives\*.audio.m4a`; ผลมีคำว่า `chives`); `test_scene_frames_capped` (สร้างวิดีโอทดสอบด้วย ffmpeg `testsrc` 10 วิ เปลี่ยนสีทุก 1 วิ, `max_frames=3` → ได้ 3 เฟรม เวลาเรียงขึ้น)
- [ ] **Step 2:** → FAIL · **Step 3:** implement · **Step 4:** `pytest -q` และ `pytest -q -m gpu` → PASS · commit `feat: transcriber seam and scene frame extraction`

### Task 8: Ingest orchestrator + Advisor scaffold

**Files:**
- Create: `src/brainsuck/ingest.py`, `src/brainsuck/advisor.py`
- Create: `plugins/brain-sucker/templates/advisor-claude.md`
- Test: `tests/test_ingest.py`, `tests/test_advisor.py`

**Interfaces:**
- Consumes: Task 2–7 ทั้งหมด
- Produces:
  - `advisor.ensure_advisor(advisor_dir: Path, domain: str | None) -> None` — ถ้าไม่มี `CLAUDE.md`: ต้องมี `domain` (ไม่งั้น raise `AdvisorMissing`) แล้วเขียนจาก template (แทน `{{domain}}`) · ถ้ามีอยู่แล้วไม่แตะส่วนนอก managed block
  - `advisor.update_channel_list(advisor_dir: Path) -> None` — เขียนรายชื่อ Channel (title, handle, จำนวน Video) ระหว่าง `<!-- brain-sucker:channels:start -->` / `<!-- brain-sucker:channels:end -->`
  - `channel_folder_name(handle: str | None, channel_id: str) -> str` — handle ตัด `@`, lowercase, แทนอักขระที่ใช้ไม่ได้บน Windows (`<>:"/\|?*`) ด้วย `-`, ถ้าว่างใช้ `channel_id`
  - `IngestResult(new: int, refreshed: int, removed: int, skipped: int, blocked: bool)`
  - `ingest(channel_id: str, advisor_dir: Path, *, yt: YouTube, make_transcriber: Callable[[], Transcriber], cache_dir: Path, domain: str | None = None, screen_text: bool = False, limit: int | None = None, emit: Callable[[dict], None] = lambda e: None) -> IngestResult`

ลำดับใน `ingest`: `ensure_advisor` → `list_channel` → โหลด/สร้าง state (โฟลเดอร์ Channel ตั้งครั้งแรกแล้วไม่เปลี่ยน) → `plan_sync` → removed/restored → refresh (fetch_info + `refresh_metadata`) → new ทีละคลิป (fetch_info → `choose_source` → captions หรือ audio+Whisper → frames ถ้า `screen_text` → `write_record` → อัปเดต `known` → `save_state` **หลังทุกคลิป**) → ลบไฟล์ใน cache ของคลิปนั้น → `write_index`, `write_skipped`, `update_channel_list`. `make_transcriber` เรียกครั้งเดียวเมื่อต้องใช้ครั้งแรก. `Unavailable` → skipped พร้อม reason. `Blocked` → `save_state`, emit `{"event":"blocked"}`, คืน `blocked=True` (ไม่นับเป็น skipped). `emit` events: `{"event":"start","total_new":n}`, `{"event":"video","id":…,"source":…,"i":k,"n":n}`, `{"event":"skipped","id":…,"reason":…}`, `{"event":"done",…IngestResult}`

Template `advisor-claude.md` มี: หัวข้อ Advisor ด้าน `{{domain}}`, บรรทัด "ก่อนตอบทุกคำถามในโฟลเดอร์นี้ ให้โหลด skill `brain-sucker:advisor` เสมอ", managed block รายชื่อ Channel, และ "เพิ่ม/อัปเดตช่องด้วย `/brain-sucker:brain-suck <ช่อง>`"

- [ ] **Step 1: failing tests** (ใช้ `FixtureYouTube` + `FakeTranscriber`, advisor dir ชื่อ `"ที่ปรึกษา ทำอาหาร"`)
  - `test_first_ingest_creates_advisor_and_records`: 4 คลิป → 4 ไฟล์ใน `videos/`, `CLAUDE.md` มี domain, `index.md` 4 แถว
  - `test_requires_domain_for_new_advisor` → `AdvisorMissing`
  - `test_thai_uses_whisper_english_uses_captions`: คลิปไทย `transcript_source == "whisper-large-v3"`, อังกฤษ `"youtube-manual"`/`"youtube-auto"`; `FakeTranscriber.calls == 1`
  - `test_english_only_never_builds_transcriber`: factory ที่ raise ถ้าถูกเรียก → ingest ช่องอังกฤษผ่าน
  - `test_rerun_is_noop`: ingest ซ้ำ → `IngestResult(new=0, …)`, mtime ของ records ไม่เปลี่ยน
  - `test_blocked_midway_then_resume`: `blocked_after=2` → `blocked=True`, 2 records, state มี 2 · รันใหม่ด้วย fixture ปกติ → new=2, รวม 4, ไม่มีซ้ำ
  - `test_unavailable_goes_to_skipped`: members-only → `skipped.md` มี id + `members-only`, ไม่มี record
  - `test_removed_marks_status`: รันที่ 2 listing ไม่มี 1 คลิป → record นั้น `status: removed`, ไฟล์ยังอยู่
  - `test_refresh_preserves_summary`: แก้ record ให้ `summary: done` + summary_md → รันที่ 2 title ใหม่ → title เปลี่ยน, summary เดิม
  - `test_channel_folder_name`: `"@NicksKitchen"` → `"nickskitchen"`, `"@ครัว:บ้าน"` → `"ครัว-บ้าน"`, `None` → channel_id
  - `test_cache_cleaned`: หลัง ingest ไม่มีไฟล์เสียงใน `cache_dir`
- [ ] **Step 2:** → FAIL · **Step 3:** implement · **Step 4:** → PASS · commit `feat: ingest orchestrator and advisor scaffold`

### Task 9: CLI commands `resolve` / `ingest` / `status` + `bin/brainsuck`

**Files:**
- Modify: `src/brainsuck/cli.py`
- Create: `src/brainsuck/status.py`
- Create: `plugins/brain-sucker/bin/brainsuck` (bash)
- Test: `tests/test_cli.py`, `tests/test_status.py`

**Interfaces:**
- Consumes: `ingest`, `YtDlpYouTube`, `FasterWhisperTranscriber`, `ChannelStore`
- Produces (CLI ตาม `docs/DESIGN.md` § ①):
  - `brainsuck resolve <query>` → stdout JSON list ของ `ChannelCandidate`
  - `brainsuck ingest <channel_id> --advisor <dir> [--domain <text>] [--screen-text] [--limit N]` → JSON lines (`emit`) · exit 0 ปกติ, **exit 2 เมื่อ blocked**, exit 3 เมื่อ `AdvisorMissing`, exit 4 เมื่อ `SuspiciousListing`
  - `brainsuck status <advisor_dir>` → JSON `{"channels":[{"folder","channel_id","title","videos","pending":[<path>…],"needs_synthesis":bool}]}` · `needs_synthesis` = จำนวน record `summary: done` ≠ ค่า `covers` ใน front-matter ของ `topics.md` (ไม่มีไฟล์ = 0)
  - `status.collect_status(advisor_dir: Path) -> dict`
- `bin/brainsuck`: หา plugin root จาก `dirname "${BASH_SOURCE[0]}"/..`; `CACHE="${BRAINSUCK_CACHE:-/c/brain-sucker-cache}"`; ถ้าไม่มี `$CACHE/venv/Scripts/python.exe` หรือ hash ของ `cli/pyproject.toml` ไม่ตรงกับ `$CACHE/venv/.stamp` → สร้าง venv + `pip install -e "<root>/cli[asr]"` + เขียน stamp; แล้ว `exec "$PY" -m brainsuck "$@"` · ทุก path ครอบ `"…"`

- [ ] **Step 1: failing tests** — `test_ingest_exit_code_blocked` (inject fixture ผ่าน `main(argv, yt=..., make_transcriber=...)`), `test_ingest_exit_code_missing_domain`, `test_status_pending_and_needs_synthesis` (2 records: 1 pending 1 done, ไม่มี topics.md → `needs_synthesis: true`), `test_status_thai_path_utf8` (stdout decode utf-8 ได้, มีชื่อไทย ไม่ใช่ `\u0e..`)
- [ ] **Step 2:** → FAIL · **Step 3:** implement · **Step 4:** → PASS
- [ ] **Step 5:** manual: `bash plugins/brain-sucker/bin/brainsuck resolve "Nick's Kitchen"` (ครั้งแรกสร้าง venv) → candidate แรก id `UC2HNqPgeKtVr2gZmLeeIk3g`
- [ ] **Step 6:** commit `feat: brainsuck CLI and bin wrapper`

### Task 10: Agents (summarizer + synthesizers)

**Files:**
- Create: `plugins/brain-sucker/agents/video-summarizer.md` (`model: haiku`, tools: Read, Edit, Glob)
- Create: `plugins/brain-sucker/agents/channel-synthesizer.md` (`model: opus`, tools: Read, Write, Glob, Grep)
- Create: `plugins/brain-sucker/agents/advisor-synthesizer.md` (`model: opus`, tools: Read, Write, Glob)

เขียน prompt ด้วย skill `mattpocock-skills:writing-for-agents`. สัญญาที่ prompt ต้องบังคับ:
- **video-summarizer** — input: รายการ path ≤ 10 · ต่อไฟล์: แทน `## Summary` ด้วย (1) ใจความ 2–4 ประโยค (2) ขั้นตอน/สูตร/ตัวเลขสำคัญ แต่ละข้อมี `[mm:ss]` จาก Transcript (3) คำแนะนำ/ความเห็นของเจ้าของช่องพร้อม `[mm:ss]` · ตั้ง front-matter `topics:` (3–8 คำ, ตัวพิมพ์เล็ก, ภาษาเดียวกับคลิป) และ `summary: done` · ห้ามแก้ส่วนอื่น · ถ้า `screen_frames` ไม่ว่าง → ดูภาพแล้วเขียน `## Screen Text` (`[mm:ss] ข้อความ`) · Summary เขียนภาษาเดียวกับคลิป
- **channel-synthesizer** — input: channel dir + (ถ้ามี) รายการ id ใหม่ · อ่าน `index.md` + Summary ทุกไฟล์ · เขียน `topics.md` (front-matter `covers: <จำนวน record ที่ summary: done>`; Topic → รายการ Video พร้อมวันที่), `principles.md` (หลักการที่เห็นซ้ำ ≥ 2 Video พร้อม Citation), `evolution.md` (ความเห็นที่เปลี่ยน: เดิม (วันที่, Citation) → ใหม่ (วันที่, Citation)), `glossary.md` · ใช้ Recency Weighting เมื่อขัดกัน
- **advisor-synthesizer** — input: advisor dir · อ่าน `topics/principles/evolution` ทุก Channel · เขียน `advisor.md`: Topic รวม, จุดที่ Channel เห็นตรงกัน, จุดที่เห็นต่าง (แต่ละฝั่งพร้อม Citation, ไม่ตัดสินด้วยความใหม่), Channel ไหนเด่นเรื่องอะไร

- [ ] **Step 1:** เขียน 3 ไฟล์
- [ ] **Step 2: verify summarizer** — copy record `K_SXQoMdSf4` จาก Task 9 manual run ไป tmp, เรียก agent `brain-sucker:video-summarizer` → `summary: done`, มี `[mm:ss]` ≥ 3 จุด, `## Transcript` ไม่เปลี่ยน (diff)
- [ ] **Step 3: verify synthesizer** บน 5 records ที่สรุปแล้ว → `topics.md` มี `covers: 5`, ทุก bullet ใน `principles.md` มี Citation
- [ ] **Step 4:** commit `feat: summarizer and synthesizer agents`

### Task 11: Skills `brain-suck` + `advisor`

**Files:**
- Create: `plugins/brain-sucker/skills/brain-suck/SKILL.md`
- Create: `plugins/brain-sucker/skills/advisor/SKILL.md`

เขียนด้วย `superpowers:writing-skills`.
- **brain-suck** (`allowed-tools` อนุญาต `Bash(brainsuck *)`) — ขั้นตอน: (1) ถ้าโฟลเดอร์ปัจจุบันยังไม่มี `CLAUDE.md` ถาม "ที่ปรึกษาด้านอะไร" (2) `brainsuck resolve` → ถ้า > 1 candidate แสดง 3 อันดับพร้อม subscribers ให้ผู้ใช้เลือก (3) `brainsuck ingest … --advisor "<cwd>"` แบบ background แล้วรายงานความคืบหน้าจาก JSON lines; exit 2 → แจ้งว่าโดนบล็อก ให้รันซ้ำทีหลัง (4) `brainsuck status` → แบ่ง `pending` เป็น batch ละ 10 → เรียก agent `brain-sucker:video-summarizer` ขนานกัน ≤ 8 ตัว จนหมด แล้วลบโฟลเดอร์เฟรมใน cache ของ record ที่ `summary: done` (5) ถ้า `needs_synthesis` → `brain-sucker:channel-synthesizer` → `brain-sucker:advisor-synthesizer` (6) สรุปผล: จำนวน Video, Skipped Video, ตัวอย่างคำถามที่ถามได้ · option `--screen-text`, `--limit N` ส่งต่อให้ CLI
- **advisor** — description ให้ trigger เมื่ออยู่ในโฟลเดอร์ที่ `CLAUDE.md` ระบุว่าเป็น Brain Sucker Advisor · เนื้อหา = กฎการตอบ 7 ข้อจาก `docs/PLAN.md` § กฎการตอบของที่ปรึกษา (คัดลอกตรงตัว) + วิธีค้น: `advisor.md` → `channels/*/topics.md` → grep `videos/` → อ่าน Transcript รอบ timestamp · Citation รูปแบบ `[ชื่อคลิป @ mm:ss](https://youtu.be/<id>?t=<วินาที>)` · Removed Video ต่อท้าย "(คลิปนี้ไม่อยู่บน YouTube แล้ว)"

- [ ] **Step 1:** เขียน 2 skills
- [ ] **Step 2:** `anthropic-skills:skill-creator` eval การ trigger: `advisor` ต้อง trigger เมื่อถามเรื่องอาหารในโฟลเดอร์ Advisor และไม่ trigger ในโฟลเดอร์อื่น
- [ ] **Step 3:** commit `feat: brain-suck and advisor skills`

### Task 12: ติดตั้ง + E2E

- [ ] **Step 1:** `claude plugin validate .` → ผ่าน · `claude plugin marketplace add "C:\Users\Lenovo\OneDrive\Desktop\brain sucker"` · `claude plugin install brain-sucker@brain-sucker-local`
- [ ] **Step 2:** สร้างโฟลเดอร์ `ที่ปรึกษาทำอาหาร` (นอก repo) → `/brain-sucker:brain-suck Nick's Kitchen` → domain "ทำอาหาร" → รอจบ: records = จำนวนคลิป Long+Short − Skipped, `pending` = 0, `advisor.md` มีอยู่
- [ ] **Step 3: golden Q&A** (บันทึกผลที่ `docs/research/0003-e2e.md`) — ถามในโฟลเดอร์นั้น:
  1. "ทำ beef bourguignon อบกี่องศา กี่ชั่วโมง" → 375°F / 3 ชม. + Citation ลิงก์ `K_SXQoMdSf4?t=` ใกล้วินาทีที่ 127
  2. "วิธีหั่นกุยช่ายให้สวย" → อ้าง Short `wrZZf2ER3ak`
  3. "จะทำ sushi ยังไง" (ถ้าไม่มีในช่อง) → บอกว่าช่องไม่ได้พูดถึง + ส่วน General Knowledge ติดป้าย
  4. คำถามที่มีคลิปเก่า/ใหม่ขัดกัน (เลือกจาก `evolution.md`) → ยึดใหม่ + บอกว่าเปลี่ยน
- [ ] **Step 4:** เพิ่มช่องทำอาหารภาษาไทย 1 ช่อง (ผู้ใช้เลือก) ในโฟลเดอร์เดียวกัน → ตรวจ Whisper ถูกใช้, `advisor.md` มีส่วนเทียบข้ามช่อง · ถามคำถามที่ทั้งสองช่องตอบ → แสดงมุมมองแยกช่อง
- [ ] **Step 5:** วัดเวลา Whisper ใหม่ตอนเครื่องว่าง บันทึกลง `0003-e2e.md` · `superpowers:verification-before-completion` · `superpowers:requesting-code-review` บนทั้ง branch
