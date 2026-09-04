# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "flask",
#     "flask_login",
#     "werkzeug",
#     "duckdb",
#     "feedparser",
#     "python-dotenv",
#     "pyyaml",
#     "requests",
#     "lxml",
#     "SalamCast",
# ]
# ///

import io
import json
import uuid
import time
import mimetypes
import os
from urllib.parse import quote, unquote
from pathlib import Path

import duckdb
import feedparser
from flask import (
    Flask,
    Response,
    abort,
    jsonify,
    render_template,
    request,
    send_file,
    send_from_directory,
)

import requests

from flask_login import (
    LoginManager, 
    UserMixin, 
    login_user, 
    logout_user, 
    login_required, 
    current_user,
)

from werkzeug.security import generate_password_hash, check_password_hash

from dotenv import load_dotenv

load_dotenv()

# Import SalamCast RSS Generator
from salamcast import SalamCastGen

TITLE = os.getenv("TITLE", "My Podcast Server")
EMAIL = os.getenv("EMAIL", "webmaster@mysite.com")
FILES_DB = os.getenv("DB", os.getenv("PLAYLIST_DB", "database/PodcastSrv.duckdb"))

app = Flask(__name__)
app.config["SERVER_ADMIN"] = EMAIL


app.secret_key = "super-secret-key-change-this-in-production"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

FILE_DIR = os.getenv("FILE_DIR", "media/")

FEEDS = {}

# Helper function assuming you have a shared DB connection function
def get_db():
    return duckdb.connect(FILES_DB)

#     return playlist_files, feeds_dict
def get_playlists_feeds():
    """Groups distinct playlists dynamically by their parent directory path, stripping out base media path."""
    playlist_files = []
    feeds_dict = {}

    if not os.path.exists(FILES_DB):
        return playlist_files, feeds_dict

    try:
        con = get_db() # duckdb.connect(FILES_DB)
        # Query distinct playlist paths and their full directory paths
        rows = con.execute(
            """
            SELECT DISTINCT playlist, dir 
            FROM FilesCast 
            WHERE playlist IS NOT NULL AND dir IS NOT NULL 
            ORDER BY dir ASC, playlist ASC
            """
        ).fetchall()
        con.close()

        # Group playlists by parent folder
        grouped_dirs = {}
        for playlist, dir_path in rows:
            if not playlist or not dir_path:
                continue

            # Strip off the root media dir (e.g., 'media/Podcasts/Linux' -> 'Podcasts/Linux')
            rel_path = os.path.relpath(dir_path, FILE_DIR)
            path_parts = Path(rel_path).parts

            if len(path_parts) > 1:
                parent_group = path_parts[0]  # e.g., "Podcasts"
                item_label = "/".join(path_parts[1:])  # e.g., "Linux" or "Tech/Linux"
            else:
                parent_group = "Root Playlists"
                item_label = rel_path if rel_path != "." else playlist

            filename = f"{playlist}.xml"
            feed_url = f"/media/playlists/local/{quote(filename)}"
            feeds_dict[filename] = feed_url

            if parent_group not in grouped_dirs:
                grouped_dirs[parent_group] = []

            grouped_dirs[parent_group].append({
                "xml": filename,
                "raw_name": item_label,
                "label": playlist
            })

        # Format into the template's expected layout structure
        for group_name, feed_items in grouped_dirs.items():
            playlist_files.append({
                "tag": "playlist",
                "label": group_name,  # Parent Directory (e.g., "Podcasts")
                "feed_items": feed_items,
            })

    except Exception as e:
        app.logger.error(f"Error building directory tree: {e}")

    return playlist_files, feeds_dict

def make_playlist_feed(playlist, email="podcast@podcast.srv"):
    """Generates an RSS feed using SalamCastGen for a given playlist from DuckDB."""
    playlist = unquote(playlist)

    if not os.path.exists(FILES_DB):
        return Response("Database file not found", status=404)

    con =  get_db() # duckdb.connect(FILES_DB)
    # ORDER BY title ASC instead of created_time
    rows = con.execute(
        """
        SELECT 
            title, 
            description, 
            transcript, 
            file_path, 
            mimetype, 
            size, 
            created_time, 
            modified_time
        FROM FilesCast 
        WHERE playlist = ? 
        ORDER BY title ASC, file_path ASC
    """,
        [playlist],
    ).fetchall()
    con.close()

    if not rows:
        feed = SalamCastGen()
        return feed.error_feed("404")

    feed = SalamCastGen()
    feed.enable_itunes()
    feed.set_title(playlist)
    feed.set_description(f"Podcast feed for {playlist}")
    feed.set_owner(email, email)

    for r in rows:
        title, description, transcript, file_path, mimetype, size, created_time, modified_time = r
        item_title = title if title else (os.path.basename(file_path) if file_path else "Untitled Episode")

        episode = feed.create_new_item()
        episode.set_title(item_title)

        pub_date_str = str(created_time) if created_time else (str(modified_time) if modified_time else "")

        desc_parts = []
        if description:
            desc_parts.append(description)

        episode.set_description("".join(desc_parts) if desc_parts else item_title)

        if transcript:
            episode.add_element(
                'transcript',
                f"<details><summary><strong>View Transcript</strong></summary><p style='white-space: pre-wrap;'>{transcript}</p></details>"
            )

        full_media_path = file_path if file_path else ""
        if full_media_path:
            episode.add_element('file_path', full_media_path)
        if size:
            file_size = str(size)
        elif os.path.exists(full_media_path):
            file_size = str(os.path.getsize(full_media_path))
        else:
            file_size = "4096"

        encoded_rel_path = quote(full_media_path.lstrip("/"), safe="/:")
        media_url = request.url_root.rstrip("/") + "/" + encoded_rel_path

        guessed_mime, _ = mimetypes.guess_type(full_media_path)
        final_mime = mimetype or guessed_mime or "audio/mpeg"

        episode.set_enclosure(media_url, file_size, final_mime)

        if pub_date_str:
            episode.set_date(pub_date_str)

        feed.add_item(episode)

    return feed.generate_feed()

@app.route("/")
def index():
    # Load initial feeds and playlists
    playlist_files, pl_feeds = get_playlists_feeds()
    FEEDS.update(pl_feeds)
    avfiles_html = render_template(
        "feeds.html",
        tag="avfiles",
        Files=playlist_files,
    )

    return render_template(
        "new_player.html",
        title=TITLE,
        avfiles_html=avfiles_html,
    )


@app.route("/favicon.ico")
def favicon():
    return send_from_directory("static", "favicon.ico")

@app.route("/fonts/<path:filename>")
def fonts(filename):
    return send_from_directory("fonts", filename)


@app.route("/media/<path:filename>")
def media(filename):
    return send_from_directory(FILE_DIR, filename)


@app.route("/media/playlists/<service>/<playlist_file>")
def get_playlist(service, playlist_file):
    playlist_name = playlist_file.replace(".xml", "")
    return make_playlist_feed(playlist_name, app.config["SERVER_ADMIN"])

@app.route("/api/feed/<path:feed_id>")
def get_feed(feed_id):
    # Load initial feeds and playlists
    playlist_files, pl_feeds = get_playlists_feeds()
    FEEDS.update(pl_feeds)
    decoded_feed_id = unquote(feed_id)
    # feed_url = FEEDS.get(decoded_feed_id) or FEEDS.get(f"{decoded_feed_id}.xml")
    feed_url = FEEDS.get(decoded_feed_id)

    if not feed_url:
        return jsonify({"error": f"Feed '{decoded_feed_id}' not found"}), 404

    if feed_url.startswith("http://") or feed_url.startswith("https://"):
        target_url = feed_url
    else:
        # Properly percent-encode the path to handle spaces and special characters
        encoded_path = quote(feed_url, safe="/:")
        target_url = request.url_root.rstrip("/") + encoded_path

    parsed = feedparser.parse(target_url)

    items = []
    for entry in parsed.entries:
        enclosure = entry.enclosures[0] if entry.get("enclosures") else None
	# In your app.py get_feed route:
        items.append({
            "title": entry.get("title"),
            "media_url": enclosure.href if enclosure else None,
            "media_type": enclosure.type if enclosure else None,
            "description": entry.get("summary", "") or entry.get("description", ""),
            "pubDate": entry.get("published", "") or entry.get("updated", ""),
            # Raw DB fields for the edit modal:
            "file_path": entry.get("file_path", ""),
            "playlist": feed_id,
            "transcript": entry.get("transcript", "")
            
        })

    return jsonify({
        "title": parsed.feed.get("title", "Untitled Feed"),
        "description": parsed.feed.get("description", ""),
        "link": target_url,
        "items": items,
    })

@app.route("/api/episode/update", methods=["POST"])
def update_episode():
    """Updates episode metadata in the FilesCast table based on primary key file_path."""
    data = request.get_json() or {}
    file_path = data.get("file_path")

    if not file_path:
        return jsonify({"status": "error", "message": "Missing file_path primary key"}), 400

    if not os.path.exists(FILES_DB):
        return jsonify({"status": "error", "message": "Database not found"}), 404

    try:
        con =  get_db() # duckdb.connect(FILES_DB)
        # Fixed syntax: removed trailing comma after description = ?
        con.execute(
            """
            UPDATE FilesCast
            SET title = ?,
                description = ?
            WHERE file_path = ?
            """,
            [
                data.get("title", ""),
                data.get("description", ""),
                file_path,
            ],
        )
        con.close()
        return jsonify({"status": "success", "message": "Episode updated successfully!"})
    except Exception as e:
        app.logger.error(f"Error updating episode: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/playlist/update", methods=["POST"])
def update_playlist():
    """Renames all occurrences of a playlist name in FilesCast."""
    data = request.get_json() or {}
    old_name = data.get("old_name")
    new_name = data.get("new_name")

    if not old_name or not new_name:
        return jsonify({"status": "error", "message": "Both old_name and new_name are required"}), 400

    if not os.path.exists(FILES_DB):
        return jsonify({"status": "error", "message": "Database not found"}), 404

    try:
        con = get_db() # duckdb.connect(FILES_DB)
        con.execute(
            "UPDATE FilesCast SET playlist = ? WHERE playlist = ?",
            [new_name, old_name],
        )
        con.close()
        return jsonify({"status": "success", "message": "Playlist renamed successfully!"})
    except Exception as e:
        app.logger.error(f"Error updating playlist: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# --- User Model ---
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    res = conn.execute("SELECT id, username FROM users WHERE id = ?", [user_id]).fetchone()
    conn.close()
    return User(res[0], res[1]) if res else None

# --- Auth Endpoints ---

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    user_id = str(uuid.uuid4())
    p_hash = generate_password_hash(password)

    conn = get_db()
    try:
        conn.execute("INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)", 
                     [user_id, username, p_hash])
        conn.close()
        return jsonify({"status": "user_created"}), 201
    except Exception:
        conn.close()
        return jsonify({"error": "Username already exists"}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get('username')
    password = data.get('password')

    conn = get_db()
    res = conn.execute("SELECT id, password_hash FROM users WHERE username = ?", [username]).fetchone()
    conn.close()

    if res and check_password_hash(res[1], password):
        user = User(id=res[0], username=username)
        login_user(user)
        return jsonify({"status": "logged_in", "username": username})
    
    return jsonify({"error": "Invalid username or password"}), 401

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"status": "logged_out"})


# --- Protected Tracking Endpoints ---

@app.route('/api/media/state', methods=['GET'])
@login_required
def get_media_state():
    file_path = request.args.get('file_path')
    if not file_path:
        return jsonify({"error": "file_path is required"}), 400

    conn = get_db()
    
    state = conn.execute("""
        SELECT 
            COALESCE(p.last_position_seconds, 0.0) AS resume_position,
            COALESCE(v.views_count, 0) AS views
        FROM FilesCast f
        LEFT JOIN media_progress p ON f.file_path = p.file_path AND p.user_id = ?
        LEFT JOIN media_views v ON f.file_path = v.file_path
        WHERE f.file_path = ?
    """, [current_user.id, file_path]).fetchone()

    notes_res = conn.execute("""
        SELECT note_id, timestamp_seconds, content 
        FROM media_notes 
        WHERE user_id = ? AND file_path = ? 
        ORDER BY timestamp_seconds ASC
    """, [current_user.id, file_path]).fetchall()

    conn.close()

    return jsonify({
        "resume_position": state[0] if state else 0.0,
        "views": state[1] if state else 0,
        "notes": [{"id": n[0], "timestamp": n[1], "content": n[2]} for n in notes_res]
    })
#
@app.route('/api/media/save-position', methods=['POST'])
@login_required
def save_position():
    data = request.get_json(silent=True) or {}
    file_path = data.get('file_path')
    position = data.get('position', 0.0)

    if not file_path:
        return jsonify({"error": "file_path is required"}), 400

    # Retry loop to handle concurrent write collisions safely
    for attempt in range(3):
        try:
            conn = get_db()
            conn.execute("""
                INSERT INTO media_progress (user_id, file_path, last_position_seconds, updated_at)
                VALUES (?, ?, ?, now())
                ON CONFLICT(user_id, file_path) DO UPDATE SET
                    last_position_seconds = EXCLUDED.last_position_seconds,
                    updated_at = now()
            """, [current_user.id, file_path, position])
            conn.close()
            return jsonify({"status": "success"})
        except duckdb.TransactionException:
            if 'conn' in locals():
                conn.close()
            time.sleep(0.05) # Wait 50ms before retrying

    return jsonify({"error": "Database busy"}), 500
#

@app.route('/api/media/view', methods=['POST'])
@login_required
def increment_view():
    data = request.get_json(silent=True) or {}
    file_path = data.get('file_path')

    if not file_path:
        return jsonify({"error": "file_path is required"}), 400

    conn = get_db()
    conn.execute("""
        INSERT INTO media_views (file_path, views_count)
        VALUES (?, 1)
        ON CONFLICT(file_path) DO UPDATE SET
            views_count = views_count + 1
    """, [file_path])
    
    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/media/notes', methods=['POST'])
@login_required
def add_note():
    data = request.get_json(silent=True) or {}
    file_path = data.get('file_path')

    if not file_path or 'content' not in data:
        return jsonify({"error": "file_path and content are required"}), 400

    note_id = str(uuid.uuid4())
    conn = get_db()
    conn.execute("""
        INSERT INTO media_notes (note_id, user_id, file_path, timestamp_seconds, content)
        VALUES (?, ?, ?, ?, ?)
    """, [note_id, current_user.id, file_path, data.get('timestamp', 0.0), data.get('content', '')])
    
    conn.close()
    return jsonify({"status": "created", "note_id": note_id}), 201

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
