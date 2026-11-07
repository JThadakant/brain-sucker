---
name: mini-brain
description: Use when the user pastes YouTube / TikTok / Instagram video URLs to watch, remember or discuss ("/mini-brain <url...>"), or asks a question of their personal clip library ("/mini-brain <คำถาม>").
argument-hint: <url...> [--no-visual] [--refresh] [--to <Advisor>] | <คำถาม>
allowed-tools: Bash(brainsuck *)
---

# Mini Brain

The user's personal advisor built from single Clips they found interesting. Every Clip lives in **one Clip Library** (`brainsuck clip-status` prints its path); the current folder is only where the conversation happens.

**Two hard rules:**
- Never create or write any file in the current working directory. Temporary files go in your scratchpad.
- Never ask for a password, email, or any account detail.

`brainsuck` is on PATH (the plugin's `bin/`) and prints JSON. Its first run installs its own Python environment, which takes several minutes — tell the user.

Pick the mode from the arguments: any `http` URL → **URL mode**; text without a URL → **Question mode**; nothing → **Library mode**.

## URL mode

### 1. Fetch

Run in the background: `brainsuck clip <url>... [--no-visual] [--refresh] [--to "<Advisor>"]` (pass through the user's flags). It streams JSON lines: `start`, `clip` (`status`: `new` | `existing` | `refreshed`), `skipped` (`reason`), `needs-login`, `blocked`, `done`. Tell the user that each Clip takes about 1–1.5 minutes per 10 minutes of video (Whisper transcribes everything), and report progress from the `clip` events.

Exit codes: **0** continue · **2** a site is rate-limiting — say what was saved and that re-running later resumes, then continue with what was saved · **3** the `--to` folder is not a Brain Sucker Advisor — say so and stop · **1** show the `error` message and stop.

### 2. Instagram that needs a login

If any `needs-login` events arrived, ask **once for the whole batch** with AskUserQuestion: "Instagram ขอให้ล็อกอินก่อนดูคลิปนี้ — ใช้การล็อกอิน Instagram ที่มีอยู่ใน browser ของคุณไหม?" with the options **ใช่** / **ไม่** / **ใช่ทุกครั้ง**.

- **ใช่** → re-run `brainsuck clip <those urls> --ig-cookies auto` (it tries Edge, then Firefox, then Chrome). **ใช่ทุกครั้ง** → the same plus `--remember`, so future runs use that browser without asking.
- Still `needs-login` (its `tried` list is not empty), or the user said **ไม่** → ask once: "ใช้เครดิต NexLev กับ N คลิปนี้ไหม (ได้คำบรรยายแทนคำพูดจริง)". If yes, for each URL call the NexLev tool `watch_instagram_video_and_ask` asking for a detailed, time-ordered description of everything said and shown on screen; write the answer to a scratchpad file and run `brainsuck clip-import --url <url> --text-file "<file>" [--title "<caption first line>"] [--creator "<account>"] [--to "<Advisor>"]`. If no, report those Clips as skipped.

### 3. Summarize

`brainsuck clip-status` → `pending` (absolute paths). Split into batches of **5** and dispatch the `brain-sucker:video-summarizer` agent once per batch, up to 8 at a time. Repeat until `pending` is empty (a batch that reports `failed` gets one more try). Then delete the frames folder of every summarized record whose `screen_frames` is non-empty (the folder that holds those `t*.jpg` files).

### 4. Name the Clips

`brainsuck clip-status` → `unnamed` (Clip Keys). For the unnamed Clips from this batch, propose a name for each and show **one table**:

| # | ชื่อที่เสนอ | ชื่อจริง | แพลตฟอร์ม · ผู้สร้าง | ความยาว |

A proposed name is in the user's language, at most 60 characters, and states the Clip's core takeaway (not its clickbait title). The user answers `ok` or corrects some rows; then run `brainsuck clip-name <key> "<name>"` for every Clip. This also writes the copies for `--to`.

### 5. Load into this chat

For every Clip in this batch (new, refreshed and existing), read the record file: front-matter, `## Summary` and `## Screen Text` always; the whole `## Transcript` only when `duration` ≤ 1800 seconds. For longer Clips, grep their transcript for the user's later questions instead.

Then tell the user the Clips are ready to discuss, listing each by Display Name, and flag any Clip with `transcript_quality` above 0 (some lines were hard to hear) or `transcript_source: nexlev-description` (a description, not the creator's words). From here on, answer follow-up questions from these records using the **Answer rules** below.

## Question mode

1. `brainsuck clip-status` → `library` path.
2. Read `<library>/index.md` to see what the library holds.
3. `grep` `<library>/clips/*.md` for the user's words and their likely wording in the Clip's language. Read the `## Summary` of each hit, then the `## Transcript` lines around the cited timestamp to confirm the claim and lift a quote.
4. Answer with the **Answer rules**.

## Library mode

`brainsuck clip-status` and `<library>/index.md` → tell the user how many Clips the library holds and list the 10 newest (Display Name, platform, creator), then ask what they want to do.

## Answer rules

Follow the answer shape of the `brain-sucker:advisor` skill (labelled parts, each present only when it has content), with the first part titled **จากคลิป** instead of **จากช่อง**. Every claim from a Clip ends with a Citation; quote the creator's original sentence for the key claim or two.

**Citation**:
- YouTube → `[<display_name> @ mm:ss](https://youtu.be/<id>?t=<seconds>)`
- TikTok / Instagram → `[<display_name> @ mm:ss](<url>)`
- Use `title` when a Clip has no `display_name` yet.

A claim resting on a transcript line that ends with `⟨ถอดไม่ชัด⟩` gets "(ช่วงนี้ถอดเสียงไม่ชัด)" after its Citation. A claim from a `transcript_source: nexlev-description` record gets "(จากคำบรรยายของ NexLev ไม่ใช่คำพูดจริง)".

When the library has nothing on the question, say so in one line, then answer from general knowledge under **ความรู้ทั่วไป (ไม่ได้มาจากคลิป)**, and suggest `/mini-brain <url>` for a Clip that covers it.
