---
name: brain-suck
description: Use when the user wants to ingest, add, or update a YouTube channel in the current folder so the folder becomes (or grows) a Brain Sucker Advisor — "/brain-suck <channel>", "ดูดช่อง …", "เพิ่มช่อง …".
argument-hint: <channel name | @handle | URL> [--screen-text] [--limit N]
allowed-tools: Bash(brainsuck *)
---

# Brain Suck

Turn a YouTube channel into Channel Knowledge in the **current working directory** (the Advisor), then summarize and synthesize it. `brainsuck` is on PATH (the plugin's `bin/`); it prints JSON. Its first run installs its own Python environment, which takes a few minutes — tell the user.

## 1. Advisor

If `CLAUDE.md` in the current directory lacks the line `<!-- brain-sucker:advisor -->`, ask the user which Domain this advisor covers ("ที่ปรึกษาด้านอะไร?") and pass it as `--domain "<answer>"` in step 3.

## 2. Resolve the channel

`brainsuck resolve "<query>"` → JSON list of candidates `{channel_id, title, handle, subscribers}`. With one candidate, use it. With several, show them (title, handle, subscribers) and let the user pick. With none, say so and stop.

## 3. Ingest

Run in the background: `brainsuck ingest <channel_id> --advisor "<cwd>" [--domain "<domain>"] [--screen-text] [--limit N]`. It streams JSON lines (`start`, `video`, `skipped`, `blocked`, `done`, `error`). Report progress to the user every so often from the latest `video` event (`i` of `n`). English channels take ~20 s per video; Thai channels run Whisper and take ~1–2 min per video.

When it ends, act on the exit code:
- **0** — continue.
- **2 (blocked)** — YouTube is rate-limiting. Tell the user what was saved and that re-running `/brain-sucker:brain-suck` in an hour or two resumes where it stopped; continue with step 4 for what was ingested.
- **3 (not an advisor)** — go back to step 1.
- **4 (suspicious listing)** — YouTube returned a broken video list; nothing was changed. Tell the user and stop.
- **1** — show the `error` message and stop.

## 4. Summarize

`brainsuck status "<cwd>"` → for each channel, `pending` (absolute paths of Video Records awaiting a summary). If the total pending is above 200, tell the user the count and ask whether to summarize all now or a portion; respect the answer.

Split pending paths into batches of **5** and dispatch the `brain-sucker:video-summarizer` agent once per batch, up to 8 at a time, passing the batch's paths. Repeat `brainsuck status` and dispatch until `pending` is empty for every channel (a batch that reports `failed` goes back into the next round once).

Then, for every summarized record whose front-matter `screen_frames` is non-empty, delete the folder that holds those frames.

## 5. Synthesize

For each channel with `needs_synthesis: true`, dispatch `brain-sucker:channel-synthesizer` with the channel directory (and the ids just ingested). After all channels are done, dispatch `brain-sucker:advisor-synthesizer` with the Advisor directory.

## 6. Report

Tell the user, in their language: videos ingested per channel, Skipped Videos and why (from `skipped.md`), anything still pending, and three example questions this advisor can now answer, drawn from `topics.md`. Remind them that opening Claude in this folder gives them the advisor.
