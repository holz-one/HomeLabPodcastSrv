# dircast.py

This is a script that makes a database of found Audio Video files in ./media.
The data will be used for generating podcasts per directory.
Whisper and Ollama are both implimented for generating content to discription and transcript.
Whisper is automaticly downloaded, but will run offline.

## dependancies

- uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

- ollama (qwen2.5:1.5b)

```bash
curl -fsSL https://ollama.com/install.sh | sh
# download model
ollama pull qwen2.5:1.5b

```

### Install these with apt or brew

- ffmpeg
- ffprobe

## run

Depending on your computer this can take a lot of time.
I'm using an i5-3210M @3.1 GHz, with 16 Gb Ram. 
It took almost 2 days to process around 170 mp3 and mp4 files between 20 minutes to 10 hours.
it will scan each file in 60 minute chunks to get the transcript to avoid crashing.


### Usage Options

* **Normal Run (CPU/AI):** `uv run dircast.py`
* **GPU Accelerated:** `uv run dircast.py --gpu`
* **Fast Scan (Skip AI):** `uv run dircast.py --noai`
* **Target Specific Folder:** `uv run dircast.py --dir media/my_folder`
* **Combined Flags:** `uv run dircast.py --dir media/podcasts --gpu`
* **Clean missing playlists** `uv run dircast.py --clean`

### Clean out orphaned playlists

this will also create a json file of all data that is deleted from the database called **orphaned_playlists_<timestamp>.json**  