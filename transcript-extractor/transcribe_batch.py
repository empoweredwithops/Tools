#!/opt/homebrew/bin/python3.11
"""
Batch transcription script using faster-whisper.
Usage: python3 transcribe_batch.py /path/to/videos [--model small]
"""

import os
import sys
import argparse
import subprocess
import tempfile
from pathlib import Path
from faster_whisper import WhisperModel

# Supported video/audio extensions
SUPPORTED_EXTENSIONS = {
    ".mp4", ".mkv", ".mov", ".avi", ".webm",
    ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"
}

def extract_audio(video_path: Path, tmp_dir: str) -> Path:
    """Extract audio from video file using ffmpeg."""
    audio_path = Path(tmp_dir) / (video_path.stem + ".wav")
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-q:a", "0", "-map", "a",
        "-ar", "16000", "-ac", "1",
        str(audio_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {result.stderr}")
    return audio_path

def transcribe_file(model: WhisperModel, audio_path: Path) -> str:
    """Transcribe audio file and return transcript as string."""
    segments, info = model.transcribe(str(audio_path), beam_size=5)
    print(f"  Detected language: {info.language} (probability: {info.language_probability:.2f})")
    lines = []
    for segment in segments:
        timestamp = f"[{segment.start:.1f}s --> {segment.end:.1f}s]"
        lines.append(f"{timestamp}  {segment.text.strip()}")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Batch transcribe video/audio files.")
    parser.add_argument("directory", help="Directory containing video/audio files")
    parser.add_argument("--model", default="small",
                        choices=["tiny", "base", "small", "medium", "large-v3"],
                        help="Whisper model size (default: small)")
    args = parser.parse_args()

    input_dir = Path(args.directory).resolve()
    if not input_dir.is_dir():
        print(f"Error: '{input_dir}' is not a valid directory.")
        sys.exit(1)

    # Create Transcripts output folder
    output_dir = input_dir / "Transcripts"
    output_dir.mkdir(exist_ok=True)
    print(f"Output folder: {output_dir}\n")

    # Find all supported files
    files = sorted([
        f for f in input_dir.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ])

    if not files:
        print("No supported video/audio files found in the directory.")
        sys.exit(0)

    print(f"Found {len(files)} file(s) to transcribe.")
    print(f"Loading Whisper model '{args.model}'...\n")
    model = WhisperModel(args.model, device="cpu", compute_type="int8")

    with tempfile.TemporaryDirectory() as tmp_dir:
        for i, file_path in enumerate(files, 1):
            print(f"[{i}/{len(files)}] Processing: {file_path.name}")
            try:
                # Extract audio if it's a video file
                if file_path.suffix.lower() in {".mp4", ".mkv", ".mov", ".avi", ".webm"}:
                    print("  Extracting audio...")
                    audio_path = extract_audio(file_path, tmp_dir)
                else:
                    audio_path = file_path

                # Transcribe
                print("  Transcribing...")
                transcript = transcribe_file(model, audio_path)

                # Save transcript
                output_file = output_dir / (file_path.stem + ".txt")
                output_file.write_text(transcript, encoding="utf-8")
                print(f"  Saved: {output_file.name}\n")

            except Exception as e:
                print(f"  ERROR processing {file_path.name}: {e}\n")

    print("Done! All transcripts saved to:")
    print(f"  {output_dir}")

if __name__ == "__main__":
    main()
