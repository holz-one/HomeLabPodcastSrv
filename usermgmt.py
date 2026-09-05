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
import argparse
import getpass
import sys
import uuid
from werkzeug.security import generate_password_hash
from app import get_db


def register(username, password):
    if not username or not password:
        print("error: Username and password required", file=sys.stderr)
        sys.exit(1)

    user_id = str(uuid.uuid4())
    p_hash = generate_password_hash(password)

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)",
            [user_id, username, p_hash]
        )
        conn.close()
        print(f"status: user_created (Username: {username}, ID: {user_id})")
        sys.exit(0)
    except Exception as e:
        conn.close()
        print(f"error: Could not create user. Username may already exist. ({e})", file=sys.stderr)
        sys.exit(1)


def reset_password(username, new_password):
    if not username or not new_password:
        print("error: Username and new password required", file=sys.stderr)
        sys.exit(1)

    p_hash = generate_password_hash(new_password)

    conn = get_db()
    try:
        user = conn.execute("SELECT id FROM users WHERE username = ?", [username]).fetchone()
        if not user:
            print(f"error: User '{username}' does not exist", file=sys.stderr)
            conn.close()
            sys.exit(1)

        conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            [p_hash, username]
        )
        conn.close()
        print(f"status: password_reset_success (User: {username})")
        sys.exit(0)
    except Exception as e:
        conn.close()
        print(f"error: Could not reset password. ({e})", file=sys.stderr)
        sys.exit(1)


def delete_user(username, force=False):
    if not username:
        print("error: Username is required", file=sys.stderr)
        sys.exit(1)

    conn = get_db()
    try:
        user = conn.execute("SELECT id FROM users WHERE username = ?", [username]).fetchone()
        if not user:
            print(f"error: User '{username}' does not exist", file=sys.stderr)
            conn.close()
            sys.exit(1)

        user_id = user[0]

        if not force:
            confirm = input(f"Are you sure you want to delete user '{username}' and all associated data? (y/N): ").strip().lower()
            if confirm != 'y':
                print("Operation canceled.")
                conn.close()
                sys.exit(0)

        conn.execute("DELETE FROM media_progress WHERE user_id = ?", [user_id])
        conn.execute("DELETE FROM media_notes WHERE user_id = ?", [user_id])
        conn.execute("DELETE FROM users WHERE id = ?", [user_id])

        conn.close()
        print(f"status: user_deleted (Username: {username}, ID: {user_id})")
        sys.exit(0)

    except Exception as e:
        conn.close()
        print(f"error: Could not delete user '{username}'. ({e})", file=sys.stderr)
        sys.exit(1)


def list_users():
    conn = get_db()
    try:
        users = conn.execute("SELECT id, username, created_at FROM users ORDER BY username ASC").fetchall()
        conn.close()

        if not users:
            print("No users found.")
            sys.exit(0)

        print(f"{'USERNAME':<20} {'ID':<38} {'CREATED AT'}")
        print("-" * 75)
        for user_id, username, created_at in users:
            print(f"{username:<20} {user_id:<38} {created_at}")
        sys.exit(0)
    except Exception as e:
        conn.close()
        print(f"error: Could not retrieve users. ({e})", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage PodcastSrv user accounts.")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Add user subcommand
    parser_add = subparsers.add_parser("add", help="Add a new user")
    parser_add.add_argument("-u", "--username", help="Username")
    parser_add.add_argument("-p", "--password", help="Password")

    # Reset password subcommand
    parser_reset = subparsers.add_parser("reset", help="Reset password for an existing user")
    parser_reset.add_argument("-u", "--username", help="Username")
    parser_reset.add_argument("-p", "--password", help="New Password")

    # Delete user subcommand
    parser_del = subparsers.add_parser("del", help="Delete a user and associated data")
    parser_del.add_argument("-u", "--username", help="Username")
    parser_del.add_argument("-f", "--force", action="store_true", help="Skip confirmation prompt")

    # List users subcommand
    subparsers.add_parser("list", help="List all registered users")

    args = parser.parse_args()

    if args.command == "add":
        username = args.username or input("Enter username: ").strip()
        password = args.password or getpass.getpass("Enter password: ").strip()
        register(username, password)

    elif args.command == "reset":
        username = args.username or input("Enter username: ").strip()
        password = args.password or getpass.getpass("Enter new password: ").strip()
        reset_password(username, password)

    elif args.command == "del":
        username = args.username or input("Enter username to delete: ").strip()
        delete_user(username, force=args.force)

    elif args.command == "list":
        list_users()

    else:
        parser.print_help()
        sys.exit(1)