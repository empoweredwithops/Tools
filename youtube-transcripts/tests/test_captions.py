from yt_transcript.captions import (
    Segment,
    clean_line,
    dedupe_cues,
    format_timestamp,
    parse_vtt,
    to_paragraphs,
    vtt_to_markdown,
)
from yt_transcript.output import filename_for, format_duration, render_markdown, slugify

# The shape YouTube auto-captions come in: each cue repeats the previous
# line, the new line carries word-level timing tags, and tiny 10ms cues
# in between show only the old line. The \x20 lines are YouTube's
# space-only lines, written as escapes so editors don't strip them.
AUTO_VTT = """WEBVTT
Kind: captions
Language: en

00:00:00.160 --> 00:00:02.869 align:start position:0%
\x20
hi<00:00:00.520><c> everyone</c><00:00:00.880><c> welcome</c>

00:00:02.869 --> 00:00:02.879 align:start position:0%
hi everyone welcome
\x20

00:00:02.879 --> 00:00:05.480 align:start position:0%
hi everyone welcome
to<00:00:03.120><c> the</c><00:00:03.360><c> channel</c>

00:00:05.480 --> 00:00:05.490 align:start position:0%
to the channel
\x20

00:00:05.490 --> 00:00:08.000 align:start position:0%
to the channel
today<00:00:05.900><c> we</c><00:00:06.100><c> talk</c><00:00:06.400><c> escrow</c>
"""

MANUAL_VTT = """WEBVTT

NOTE This is a comment block and should be ignored.

STYLE
::cue { color: yellow; }

1
00:00:01.000 --> 00:00:03.500
<v Craig>Welcome back.</v>

2
00:00:03.500 --> 00:00:06.000
Today we&#39;re covering
closing timelines &amp; deadlines.

3
01:02:03.000 --> 01:02:05.000
Thanks for watching!
"""


def test_auto_captions_drop_scrolling_duplicates():
    text = vtt_to_markdown(AUTO_VTT)
    assert text == "hi everyone welcome to the channel today we talk escrow"


def test_dedupe_keeps_start_time_of_new_text():
    segments = dedupe_cues(parse_vtt(AUTO_VTT))
    assert [(s.start, s.text) for s in segments] == [
        (0.16, "hi everyone welcome"),
        (2.879, "to the channel"),
        (5.49, "today we talk escrow"),
    ]


def test_dedupe_handles_lines_that_grow_word_by_word():
    vtt = """WEBVTT

00:00:00.000 --> 00:00:01.000
so the buyer

00:00:01.000 --> 00:00:02.000
so the buyer signs

00:00:02.000 --> 00:00:03.000
so the buyer signs the addendum
"""
    assert vtt_to_markdown(vtt) == "so the buyer signs the addendum"


def test_manual_captions_skip_header_note_style_and_strip_tags():
    cues = parse_vtt(MANUAL_VTT)
    assert len(cues) == 3
    assert cues[0].lines == ["Welcome back."]
    assert cues[2].start == 3723.0
    assert vtt_to_markdown(MANUAL_VTT) == (
        "Welcome back. Today we're covering closing timelines & deadlines. Thanks for watching!"
    )


def test_clean_line():
    assert clean_line("  <c.colorE5E5E5>one</c>&nbsp; <00:00:01.000>two  ") == "one two"
    assert clean_line("&gt;&gt; next speaker") == ">> next speaker"


def test_windows_line_endings_and_comma_decimals():
    vtt = "WEBVTT\r\n\r\n00:01.000 --> 00:02,500\r\nshort timing form\r\n"
    cues = parse_vtt(vtt)
    assert (cues[0].start, cues[0].end, cues[0].lines) == (1.0, 2.5, ["short timing form"])


def test_paragraphs_break_at_sentence_end_once_long_enough():
    sentence = "This is a sentence with exactly ten words in it."
    segments = [Segment(i * 3.0, i * 3.0 + 3, sentence) for i in range(14)]
    paragraphs = to_paragraphs(segments).split("\n\n")
    assert len(paragraphs) == 3
    assert all(p.endswith(".") for p in paragraphs)
    assert len(paragraphs[0].split()) == 60


def test_unpunctuated_text_still_gets_paragraph_breaks():
    segments = [Segment(i, i + 1, "word " * 10) for i in range(40)]
    paragraphs = to_paragraphs(segments).split("\n\n")
    assert len(paragraphs) == 3
    assert all(len(p.split()) <= 150 for p in paragraphs)


def test_speaker_change_starts_new_paragraph():
    segments = [
        Segment(0, 1, "so what do you think"),
        Segment(1, 2, ">> I think it closes Friday"),
    ]
    assert to_paragraphs(segments) == "so what do you think\n\nI think it closes Friday"


def test_timestamps_every_interval():
    segments = [Segment(i * 5.0, i * 5.0 + 5, f"part {i}") for i in range(14)]
    text = to_paragraphs(segments, timestamp_interval=30)
    assert text.split("\n\n") == [
        "[00:00] part 0 part 1 part 2 part 3 part 4 part 5",
        "[00:30] part 6 part 7 part 8 part 9 part 10 part 11",
        "[01:00] part 12 part 13",
    ]


def test_format_timestamp_over_an_hour():
    assert format_timestamp(59.9) == "00:59"
    assert format_timestamp(3723) == "1:02:03"


def test_punctuation_spacing_is_tidied_when_joining():
    segments = [Segment(0, 1, "well"), Segment(1, 2, ", okay"), Segment(2, 3, "then .")]
    assert to_paragraphs(segments) == "well, okay then."


def test_slug_and_filename():
    assert slugify("Q3 Retro: Notes & Next Steps!") == "q3-retro-notes-next-steps"
    assert slugify("Café déjà vu") == "cafe-deja-vu"
    assert slugify("日本語") == "video"
    assert filename_for("My Video", "a-B_c123") == "my-video--a-B_c123.md"


def test_frontmatter_quotes_values_safely():
    info = {
        "id": "abc123",
        "title": 'He said "close: now"',
        "channel": "Ops Channel",
        "upload_date": "20260314",
        "duration": 3723,
    }
    md = render_markdown(info, "https://www.youtube.com/watch?v=abc123", "manual_captions", "Body.")
    assert 'title: "He said \\"close: now\\""' in md
    assert "upload_date: 2026-03-14" in md
    assert 'duration: "1:02:03"' in md
    assert "transcript_source: manual_captions" in md
    assert md.endswith("Body.\n")
    assert format_duration(65) == "1:05"


def test_empty_transcript_gets_a_note():
    info = {"id": "abc123", "title": "Music only"}
    md = render_markdown(info, "https://www.youtube.com/watch?v=abc123", "whisper", "")
    assert md.endswith("# Music only\n\n_No speech found in this video._\n")
