import sqlite3
import os
from pathlib import Path

def migrate():
    db_path = Path("data/client_local.db")
    if not db_path.exists():
        print(f"[ERROR] Database not found at {db_path}")
        return

    print(f"[INFO] Connecting to {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check columns in webwatcherconfig
    try:
        cursor.execute("PRAGMA table_info(webwatcherconfig)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"[INFO] Current columns in webwatcherconfig: {columns}")

        # Columns to add
        to_add = [
            ("send_email_on_change", "INTEGER DEFAULT 0"),
            ("smtp_credential_id", "INTEGER"),
            ("notification_email", "TEXT")
        ]

        added = 0
        for col_name, col_def in to_add:
            if col_name not in columns:
                print(f"[INFO] Adding column {col_name}...")
                cursor.execute(f"ALTER TABLE webwatcherconfig ADD COLUMN {col_name} {col_def}")
                added += 1
            else:
                print(f"[INFO] Column {col_name} already exists.")

        if added > 0:
            conn.commit()
            print(f"[SUCCESS] Migration complete. {added} columns added.")
        else:
            print("[INFO] No changes needed.")

    except sqlite3.Error as e:
        print(f"[ERROR] SQLite error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
