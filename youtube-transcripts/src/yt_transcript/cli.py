"""yt-transcript: save YouTube transcripts as Markdown files."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

from yt_dlp.utils import DownloadError

from . import fetch, whisper
from .captions import to_paragraphs, vtt_to_markdown
from .output import existing_files, filename_for, render_markdown

OUT_DIR_ENV = "YT_TRANSCRIPTS_DIR"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="yt-transcript",
        description="Save YouTube transcripts (video, playlist or channel URLs) as Markdown.",
    )
    parser.add_argument("urls", nargs="+", metavar="URL", help="YouTube video, playlist or channel URL")
    parser.add_argument(
        "-o", "--out", type=Path,
        help=f"output folder (default: ${OUT_DIR_ENV}, or ./transcripts)",
    )
    parser.add_argument("--whisper", action="store_true", help="skip captions and transcribe the audio locally")
    parser.add_argument("--model", default="small", help="Whisper model size (default: small)")
    parser.add_argument("--timestamps", action="store_true", help="start a timestamped paragraph about every 30 seconds")
    parser.add_argument(
        "--timestamp-interval", type=float, default=30.0, metavar="SECONDS",
        help="seconds between timestamps with --timestamps (default: 30)",
    )
    parser.add_argument("--force", action="store_true", help="redo videos that already have a file")
    return parser.parse_args(argv)


def resolve_out_dir(flag: Path | None) -> Path:
    if flag:
        return flag.expanduser()
    if os.environ.get(OUT_DIR_ENV):
        return Path(os.environ[OUT_DIR_ENV]).expanduser()
    return Path("transcripts")


def process_video(video_id: str, args: argparse.Namespace, out_dir: Path, tmp_dir: Path) -> str:
    """Save one video's transcript. Returns "saved" or "skipped"."""
    existing = existing_files(out_dir, video_id)
    if existing and not args.force:
        print(f"  skip  {existing[0].name} (already saved)")
        return "skipped"

    info = fetch.get_video_info(video_id)
    interval = args.timestamp_interval if args.timestamps else None
    captions = None if args.whisper else fetch.find_captions(info)

    if captions:
        source, vtt_url = captions
        body = vtt_to_markdown(fetch.download_captions(vtt_url), interval)
    else:
        source = "whisper"
        print(f"  {'' if args.whisper else 'no English captions, '}transcribing audio with {whisper.backend_name()} ({args.model})...")
        audio = fetch.download_audio(video_id, tmp_dir)
        try:
            body = to_paragraphs(whisper.transcribe(audio, args.model), interval)
        finally:
            audio.unlink(missing_ok=True)

    path = out_dir / filename_for(info.get("title") or video_id, video_id)
    path.write_text(render_markdown(info, fetch.video_url(video_id), source, body), encoding="utf-8")
    for old in existing:
        if old != path:
            old.unlink()
    print(f"  saved {path.name} ({source})")
    return "saved"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not shutil.which("ffmpeg"):
        print(
            "ffmpeg isn't installed or isn't on your PATH. yt-transcript needs it for audio.\n"
            "Install it with:  brew install ffmpeg",
            file=sys.stderr,
        )
        return 1

    out_dir = resolve_out_dir(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Saving to {out_dir.resolve()}")

    counts = {"saved": 0, "skipped": 0, "failed": 0}
    with tempfile.TemporaryDirectory(prefix="yt-transcript-") as tmp:
        for url in args.urls:
            try:
                video_ids = fetch.list_video_ids(url)
            except DownloadError as exc:
                print(f"Couldn't read {url}: {exc}", file=sys.stderr)
                counts["failed"] += 1
                continue
            print(f"{url}: {len(video_ids)} video(s)")
            for n, video_id in enumerate(video_ids, 1):
                print(f"[{n}/{len(video_ids)}] {video_id}")
                try:
                    counts[process_video(video_id, args, out_dir, Path(tmp))] += 1
                except (DownloadError, whisper.WhisperUnavailable) as exc:
                    print(f"  failed: {exc}", file=sys.stderr)
                    counts["failed"] += 1

    print(f"Done. {counts['saved']} saved, {counts['skipped']} skipped, {counts['failed']} failed.")
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
