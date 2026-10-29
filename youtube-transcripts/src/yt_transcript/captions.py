"""Turn WebVTT captions (or Whisper segments) into readable Markdown paragraphs.

No network access here, so this is the part the tests cover.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

TIMING_RE = re.compile(
    r"^\s*((?:\d+:)?\d{1,2}:\d{2}[.,]\d{3})\s+-->\s+((?:\d+:)?\d{1,2}:\d{2}[.,]\d{3})"
)
TAG_RE = re.compile(r"<[^>]*>")
SENTENCE_END_RE = re.compile(r"[.!?…][\"')\]]*$")
SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.!?;:])")

# Paragraph sizing when timestamps are off.
MIN_PARAGRAPH_WORDS = 60
MAX_PARAGRAPH_WORDS = 150
PAUSE_SECONDS = 2.0


@dataclass
class Cue:
    start: float
    end: float
    lines: list[str]


@dataclass
class Segment:
    start: float
    end: float
    text: str


def parse_timestamp(value: str) -> float:
    parts = value.replace(",", ".").split(":")
    seconds = float(parts[-1])
    minutes = int(parts[-2])
    hours = int(parts[-3]) if len(parts) == 3 else 0
    return hours * 3600 + minutes * 60 + seconds


def clean_line(line: str) -> str:
    """Strip inline timing/style tags and entities, collapse whitespace."""
    line = TAG_RE.sub("", line)
    line = html.unescape(line).replace(" ", " ")
    return " ".join(line.split())


def parse_vtt(text: str) -> list[Cue]:
    cues = []
    # Split on truly empty lines only: auto-captions put a line holding a
    # single space inside a cue, and that must not end the cue.
    blocks = re.split(r"\n{2,}", text.replace("\r\n", "\n").replace("\r", "\n"))
    for block in blocks:
        lines = block.split("\n")
        for i, line in enumerate(lines):
            match = TIMING_RE.match(line)
            if match:
                cues.append(
                    Cue(
                        start=parse_timestamp(match.group(1)),
                        end=parse_timestamp(match.group(2)),
                        lines=[c for c in map(clean_line, lines[i + 1 :]) if c],
                    )
                )
                break
        # Blocks with no timing line (WEBVTT header, NOTE, STYLE) are skipped.
    return cues


def dedupe_cues(cues: list[Cue]) -> list[Segment]:
    """Collapse the repeated lines auto-captions produce as they scroll.

    YouTube auto-captions show two lines at once: the previous line again,
    plus the new one. Some tracks also grow a line word by word. Only text
    that hasn't been seen on the line before is kept.
    """
    segments = []
    last = ""
    for cue in cues:
        for line in cue.lines:
            if not line or line == last:
                continue
            if last and line.startswith(last + " "):
                new_text = line[len(last) :].strip()
            else:
                new_text = line
            segments.append(Segment(cue.start, cue.end, new_text))
            last = line
    return segments


def format_timestamp(seconds: float) -> str:
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _join(texts: list[str]) -> str:
    return SPACE_BEFORE_PUNCT_RE.sub(r"\1", " ".join(texts))


def to_paragraphs(segments: list[Segment], timestamp_interval: float | None = None) -> str:
    """Join segments into paragraphs.

    With timestamp_interval set, a new paragraph starts at the first segment
    once that many seconds have passed, and each paragraph is prefixed with
    its start time. Otherwise paragraphs break at a sentence end or pause
    once they're long enough, with a hard cap for unpunctuated captions.
    A ">>" speaker-change marker always starts a new paragraph.
    """
    paragraphs: list[tuple[float, list[str]]] = []
    words = 0
    prev_end = None

    for seg in segments:
        text = seg.text.strip()
        speaker_change = text.startswith(">>")
        if speaker_change:
            text = text.lstrip(">").strip()
        if not text:
            continue

        if not paragraphs:
            new_paragraph = True
        elif speaker_change:
            new_paragraph = True
        elif timestamp_interval is not None:
            new_paragraph = seg.start - paragraphs[-1][0] >= timestamp_interval
        else:
            at_sentence_end = bool(SENTENCE_END_RE.search(paragraphs[-1][1][-1]))
            paused = prev_end is not None and seg.start - prev_end >= PAUSE_SECONDS
            new_paragraph = (
                words >= MIN_PARAGRAPH_WORDS and (at_sentence_end or paused)
            ) or words >= MAX_PARAGRAPH_WORDS

        if new_paragraph:
            paragraphs.append((seg.start, []))
            words = 0
        paragraphs[-1][1].append(text)
        words += len(text.split())
        prev_end = seg.end

    out = []
    for start, texts in paragraphs:
        body = _join(texts)
        if timestamp_interval is not None:
            body = f"[{format_timestamp(start)}] {body}"
        out.append(body)
    return "\n\n".join(out)


def vtt_to_markdown(vtt: str, timestamp_interval: float | None = None) -> str:
    return to_paragraphs(dedupe_cues(parse_vtt(vtt)), timestamp_interval)
