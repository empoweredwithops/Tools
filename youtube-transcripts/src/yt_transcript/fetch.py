"""Everything that talks to YouTube, via yt-dlp."""

from __future__ import annotations

from pathlib import Path

import yt_dlp

MANUAL_LANG_PREFS = ["en", "en-US", "en-GB"]
# "en-orig" is the untranslated speech-recognition track on English videos.
AUTO_LANG_PREFS = ["en-orig", "en"]


def _ydl(**opts) -> yt_dlp.YoutubeDL:
    base = {"quiet": True, "no_warnings": True, "noprogress": True}
    base.update(opts)
    return yt_dlp.YoutubeDL(base)


def list_video_ids(url: str) -> list[str]:
    """Expand a video, playlist or channel URL into video IDs."""
    ids: list[str] = []
    with _ydl(extract_flat="in_playlist", skip_download=True) as ydl:
        _collect(ydl, ydl.extract_info(url, download=False), ids)
    seen = set()
    return [i for i in ids if not (i in seen or seen.add(i))]


def _collect(ydl: yt_dlp.YoutubeDL, info: dict, ids: list[str]) -> None:
    if info.get("_type") not in ("playlist", "multi_video"):
        ids.append(info["id"])
        return
    for entry in info.get("entries") or []:
        if not entry:
            continue
        if entry.get("_type") == "playlist":
            _collect(ydl, entry, ids)
        elif entry.get("ie_key") == "YoutubeTab":
            # A channel lists its tabs (Videos, Shorts, Live) as nested playlists.
            _collect(ydl, ydl.extract_info(entry["url"], download=False), ids)
        elif entry.get("id"):
            ids.append(entry["id"])


def get_video_info(video_id: str) -> dict:
    with _ydl(skip_download=True) as ydl:
        info = ydl.extract_info(video_url(video_id), download=False)
        return ydl.sanitize_info(info)


def video_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def _pick_track(tracks: dict, prefs: list[str], strict: bool = False) -> str | None:
    if strict:
        english = [lang for lang in prefs if lang in tracks]
    else:
        english = [lang for lang in tracks if lang == "en" or lang.startswith("en-")]
    english.sort(key=lambda lang: (prefs.index(lang) if lang in prefs else len(prefs), lang))
    for lang in english:
        for fmt in tracks[lang]:
            if fmt.get("ext") == "vtt" and fmt.get("url"):
                return fmt["url"]
    return None


def find_captions(info: dict) -> tuple[str, str] | None:
    """Return (transcript_source, vtt_url) for the best English track, if any."""
    url = _pick_track(info.get("subtitles") or {}, MANUAL_LANG_PREFS)
    if url:
        return "manual_captions", url
    # Auto-captions also list machine translations into English, so only the
    # exact keys are accepted there.
    url = _pick_track(info.get("automatic_captions") or {}, AUTO_LANG_PREFS, strict=True)
    if url:
        return "auto_captions", url
    return None


def download_captions(vtt_url: str) -> str:
    with _ydl() as ydl:
        return ydl.urlopen(vtt_url).read().decode("utf-8")


def download_audio(video_id: str, dest_dir: Path) -> Path:
    """Download the audio-only stream into dest_dir and return its path."""
    opts = {"format": "bestaudio/best", "outtmpl": str(dest_dir / "%(id)s.%(ext)s")}
    with _ydl(**opts) as ydl:
        info = ydl.extract_info(video_url(video_id), download=True)
        downloads = info.get("requested_downloads") or []
        if downloads and downloads[0].get("filepath"):
            return Path(downloads[0]["filepath"])
        return Path(ydl.prepare_filename(info))
