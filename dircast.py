# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "duckdb",
#     "pandas",
#     "python-dotenv",
#     "faster-whisper",
#     "ollama",
# ]
# ///

import argparse
import gc
import math
import mimetypes
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import duckdb
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

# Configuration
DEFAULT_FILE_DIR = os.getenv("FILE_DIR", "media/")
FILES_DB = os.getenv("DB", "database/PodcastSrv.duckdb")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")

os.makedirs(os.path.dirname(FILES_DB), exist_ok=True)
os.makedirs(DEFAULT_FILE_DIR, exist_ok=True)

HTML5_MEDIA_EXTS = {
    ".mp4", ".m4v", ".mov", # Video
    ".mp3", ".m4a", ".m4b"  # Audio
}

# Ensure DuckDB table exists on startup
def init_db():
    con = duckdb.connect(FILES_DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS FilesCast (
            playlist VARCHAR,
            title VARCHAR,
            file_path VARCHAR PRIMARY KEY,
            dir VARCHAR,
            base_dir VARCHAR,
            mimetype VARCHAR,
            size VARCHAR,
            modified_time VARCHAR,
            created_time VARCHAR,
            transcript VARCHAR,
            description VARCHAR
        )
    """)
    con.close()

def get_audio_duration(file_path: Path) -> float:
    """Returns total duration of a media file in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(file_path),
    ]
    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0

def extract_transcript(file_path: Path, whisper_model) -> str:
    """Extracts transcription from audio or video file, chunking long files (>1 hour) to save RAM."""
    duration = get_audio_duration(file_path)
    chunk_length = 3600  # 1 hour in seconds

    if duration <= chunk_length or duration == 0:
        try:
            segments, _ = whisper_model.transcribe(str(file_path), beam_size=1)
            text = " ".join([s.text.strip() for s in segments])
            return text if text else "No transcript available."
        except Exception as e:
            print(f"Whisper failed on {file_path.name}: {e}")
            return ""

    print(
        f" -> File duration is {duration / 3600:.1f} hours. Processing in 1-hour chunks..."
    )
    total_chunks = math.ceil(duration / chunk_length)
    full_transcript = []

    with tempfile.TemporaryDirectory() as temp_dir:
        for i in range(total_chunks):
            start_time = i * chunk_length
            chunk_path = Path(temp_dir) / f"chunk_{i}.wav"

            ffmpeg_cmd = [
                "ffmpeg",
                "-y",
                "-ss",
                str(start_time),
                "-i",
                str(file_path),
                "-t",
                str(chunk_length),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(chunk_path),
            ]

            subprocess.run(
                ffmpeg_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            print(
                f"    -> Transcribing chunk {i + 1}/{total_chunks} ({start_time // 60}m to {(start_time + chunk_length) // 60}m)..."
            )

            try:
                segments, _ = whisper_model.transcribe(str(chunk_path), beam_size=1)
                chunk_text = " ".join([s.text.strip() for s in segments])
                if chunk_text:
                    full_transcript.append(chunk_text)
            except Exception as e:
                print(f"Failed on chunk {i + 1}: {e}")

            if chunk_path.exists():
                chunk_path.unlink()

            gc.collect()

    return (
        " ".join(full_transcript)
        if full_transcript
        else "No transcript available."
    )

def generate_summary(transcript: str, title: str) -> str:
    """Generates a concise description using Ollama based on transcript."""
    import ollama

    if not transcript or transcript == "No transcript available.":
        return f"Media item: {title}"

    truncated_transcript = transcript[:3000]
    
    prompt = (
        f"Write a concise 2-3 sentence podcast feed summary for an episode titled '{title}'. "
        f"Base it strictly on this transcript:\n\n{truncated_transcript}\n\nSummary:"
    )

    try:
        response = ollama.generate(model=OLLAMA_MODEL, prompt=prompt)
        return response.get("response", "").strip()
    except Exception as e:
        print(f"Ollama failed on {title}: {e}")
        return transcript[:200] + "..."

def get_existing_files():
    """Returns a set of file paths already stored in DuckDB."""
    con = duckdb.connect(FILES_DB)
    rows = con.execute("SELECT file_path FROM FilesCast").fetchall()
    con.close()
    return {row[0] for row in rows}

def main():
    parser = argparse.ArgumentParser(description="Media scanner and RSS indexing database tool.")
    parser.add_argument("--dir", type=str, default=DEFAULT_FILE_DIR, help="Specific target directory to scan")
    parser.add_argument("--gpu", action="store_true", help="Enable CUDA GPU acceleration for Whisper transcription")
    parser.add_argument("--noai", action="store_true", help="Skip Whisper and Ollama, saving empty strings for transcript and description")
    args = parser.parse_args()

    init_db()

    whisper_model = None
    if not args.noai:
        device = "cuda" if args.gpu else "cpu"
        compute_type = "float16" if args.gpu else "int8"
        print(f"Loading Whisper model on device '{device}' ({compute_type})...")
        
        model_path = Path("models/whisper-base-en")
        if not model_path.exists():
            print("Downloading Whisper model locally...")
            from faster_whisper import download_model
            download_model("base.en", output_dir=str(model_path))

        from faster_whisper import WhisperModel
        whisper_model = WhisperModel(str(model_path), device=device, compute_type=compute_type)

    target_dir = Path(args.dir)

    if not target_dir.exists():
        print(f"Warning: Media directory '{target_dir}' does not exist.")
        return

    processed_files = get_existing_files()
    
    for file_path in target_dir.rglob("*"):
        str_path = str(file_path)
        
        if file_path.is_file() and file_path.suffix.lower() in HTML5_MEDIA_EXTS:
            if str_path in processed_files:
                print(f"Skipping already processed: {file_path.name}")
                continue

            playlist = file_path.parent.name
            dir_name = str(file_path.parent)
            title = file_path.stem
            
            mimetype, _ = mimetypes.guess_type(file_path)
            if not mimetype:
                mimetype = "application/octet-stream"

            mtime_raw = os.path.getmtime(file_path)
            ctime_raw = os.path.getctime(file_path)
            mtime_readable = datetime.fromtimestamp(mtime_raw).strftime("%Y-%m-%d %H:%M:%S")
            ctime_readable = datetime.fromtimestamp(ctime_raw).strftime("%Y-%m-%d %H:%M:%S")

            print(f"\nProcessing: {title} ({playlist})")
            
            if args.noai:
                transcript = ""
                description = ""
                print(" -> Skipping AI processing (--noai active)")
            else:
                print(" -> Transcribing audio...")
                transcript = extract_transcript(file_path, whisper_model)

                print(" -> Generating description with Ollama...")
                description = generate_summary(transcript, title)

            record = [{
                "playlist": str(playlist),
                "title": str(title),
                "file_path": str_path,
                "dir": str(dir_name),
                "base_dir": str(target_dir),
                "mimetype": str(mimetype),
                "size": str(os.path.getsize(file_path)),
                "modified_time": str(mtime_readable),
                "created_time": str(ctime_readable),
                "transcript": transcript,
                "description": description,
            }]
            
            df = pd.DataFrame(record)
            con = duckdb.connect(FILES_DB)
            con.execute("INSERT INTO FilesCast SELECT * FROM df")
            con.close()
            
            print(f" -> Committed {title} to DuckDB.")
            
            processed_files.add(str_path)

            del record, df, transcript, description
            gc.collect()

    print("\nFinished processing media directory.")

if __name__ == "__main__":
    main()