"""Local transcription: mlx-whisper on Apple Silicon, faster-whisper elsewhere."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .captions import Segment

MLX_REPOS = {
    "large-v3": "mlx-community/whisper-large-v3-mlx",
    "turbo": "mlx-community/whisper-large-v3-turbo",
}


class WhisperUnavailable(RuntimeError):
    pass


def backend_name() -> str:
    try:
        import mlx_whisper  # noqa: F401

        return "mlx-whisper"
    except ImportError:
        pass
    try:
        import faster_whisper  # noqa: F401

        return "faster-whisper"
    except ImportError:
        raise WhisperUnavailable(
            "No Whisper backend installed. On Apple Silicon, mlx-whisper installs "
            "automatically; elsewhere, install with: uv sync --extra cpu"
        ) from None


def transcribe(audio_path: Path, model: str) -> list[Segment]:
    if backend_name() == "mlx-whisper":
        return _transcribe_mlx(audio_path, model)
    return _transcribe_faster(audio_path, model)


def _transcribe_mlx(audio_path: Path, model: str) -> list[Segment]:
    import mlx_whisper

    # Accept a full Hugging Face repo name, or a short size like "small".
    repo = model if "/" in model else MLX_REPOS.get(model, f"mlx-community/whisper-{model}-mlx")
    result = mlx_whisper.transcribe(str(audio_path), path_or_hf_repo=repo)
    return [Segment(s["start"], s["end"], s["text"].strip()) for s in result["segments"]]


@lru_cache(maxsize=1)
def _faster_model(model: str):
    from faster_whisper import WhisperModel

    return WhisperModel(model, device="cpu", compute_type="int8")


def _transcribe_faster(audio_path: Path, model: str) -> list[Segment]:
    segments, _info = _faster_model(model).transcribe(str(audio_path), beam_size=5)
    return [Segment(s.start, s.end, s.text.strip()) for s in segments]
