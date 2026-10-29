# yt-transcript

Saves YouTube transcripts as Markdown files for the knowledge base. Give it a video, playlist or channel URL and it writes one `.md` file per video.

It uses the video's captions when they exist (manual English captions first, then auto-generated). When there are none, it downloads just the audio and transcribes it locally with Whisper.

## Setup

You need [uv](https://docs.astral.sh/uv/) and ffmpeg:

```bash
brew install uv ffmpeg deno
```

deno (or node, if you already have it) is needed for the Whisper path. YouTube's audio URLs return 403 Forbidden unless yt-dlp can run YouTube's player code, and it needs a JavaScript runtime for that. Captions work without one.

Then, from this folder:

```bash
uv sync
```

On an Apple Silicon Mac that installs `mlx-whisper` too. On any other machine, add the CPU Whisper backend:

```bash
uv sync --extra cpu
```

To get a `yt-transcript` command you can run from anywhere:

```bash
uv tool install ./youtube-transcripts
```

(Run that from the repo root. Inside this folder, `uv run yt-transcript ...` works without installing.)

## Usage

One video:

```bash
yt-transcript https://www.youtube.com/watch?v=jNQXAC9IVRw
```

A whole playlist or channel, into your knowledge base folder:

```bash
yt-transcript --out ~/Knowledge/YouTube https://www.youtube.com/playlist?list=PL...
```

```bash
yt-transcript https://www.youtube.com/@channelname
```

Rerunning the same playlist later only picks up videos that don't have a file yet.

Set the output folder once instead of passing `--out` every time:

```bash
export YT_TRANSCRIPTS_DIR=~/Knowledge/YouTube
```

Force Whisper with a bigger model, and keep timestamps:

```bash
yt-transcript --whisper --model medium --timestamps https://youtu.be/VIDEO_ID
```

## Options

| Option | What it does |
| --- | --- |
| `-o`, `--out PATH` | Output folder. Falls back to `$YT_TRANSCRIPTS_DIR`, then `./transcripts`. |
| `--whisper` | Skip captions and transcribe the audio locally. |
| `--model NAME` | Whisper model: `tiny`, `base`, `small` (default), `medium`, `large-v3`, `turbo`. On a Mac you can also pass a full Hugging Face repo such as `mlx-community/whisper-large-v3-mlx`. |
| `--timestamps` | Start a new paragraph about every 30 seconds, prefixed with `[mm:ss]`. |
| `--timestamp-interval SECONDS` | Change that interval. |
| `--force` | Redo videos that already have a file. The old file is replaced. |

The model downloads from Hugging Face the first time you use it, then it's cached.

## Output

Files are named `slugified-title--VIDEO_ID.md`. The video ID is what the skip check looks for, so if a video's title changes it still won't be saved twice.

```markdown
---
title: "Me at the zoo"
channel: "jawed"
url: "https://www.youtube.com/watch?v=jNQXAC9IVRw"
video_id: "jNQXAC9IVRw"
upload_date: 2005-04-24
duration: "0:19"
transcript_source: manual_captions
date_captured: 2026-10-29
---

# Me at the zoo

All right, so here we are, in front of the elephants...
```

`transcript_source` is `manual_captions`, `auto_captions` or `whisper`.

## How the cleanup works

Auto-captions show each line twice as they scroll and carry word-level timing tags. The tool strips the tags and keeps only text that wasn't on the previous line. It then joins everything into paragraphs, breaking at a sentence end or pause once a paragraph is about 60 words, with a hard stop at 150 words for captions with no punctuation. A `>>` speaker-change marker always starts a new paragraph.

Downloaded audio goes in a temp folder and is deleted after each video, and the folder itself is removed when the run ends.

## If YouTube blocks you

Big channel runs can trigger YouTube's "Sign in to confirm you're not a bot" check. It usually clears up after a while. Videos that fail are reported at the end and get picked up on the next run.

## Tests

```bash
uv run pytest
```
