"""Filenames and Markdown/frontmatter for saved transcripts."""

from __future__ import annotations

import datetime as dt
import json
import re
import unicodedata
from pathlib import Path

MAX_SLUG_LENGTH = 80


def slugify(title: str) -> str:
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")
    return slug[:MAX_SLUG_LENGTH].rstrip("-") or "video"


def filename_for(title: str, video_id: str) -> str:
    return f"{slugify(title)}--{video_id}.md"


def existing_files(out_dir: Path, video_id: str) -> list[Path]:
    # Glob special characters can't appear in IDs (letters, digits, - and _).
    return sorted(out_dir.glob(f"*--{video_id}.md"))


def format_duration(seconds) -> str | None:
    if seconds is None:
        return None
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def format_upload_date(value: str | None) -> str | None:
    if value and re.fullmatch(r"\d{8}", value):
        return f"{value[:4]}-{value[4:6]}-{value[6:]}"
    return value


def _yaml_value(value) -> str:
    if value is None:
        return "null"
    # JSON strings are valid YAML double-quoted scalars.
    return json.dumps(str(value), ensure_ascii=False)


def render_markdown(info: dict, url: str, source: str, body: str) -> str:
    upload_date = format_upload_date(info.get("upload_date"))
    fields = [
        ("title", _yaml_value(info.get("title"))),
        ("channel", _yaml_value(info.get("channel") or info.get("uploader"))),
        ("url", _yaml_value(url)),
        ("video_id", _yaml_value(info["id"])),
        ("upload_date", upload_date or "null"),
        ("duration", _yaml_value(format_duration(info.get("duration")))),
        ("transcript_source", source),
        ("date_captured", dt.date.today().isoformat()),
    ]
    frontmatter = "\n".join(f"{key}: {value}" for key, value in fields)
    title = info.get("title") or info["id"]
    return f"---\n{frontmatter}\n---\n\n# {title}\n\n{body}\n"
