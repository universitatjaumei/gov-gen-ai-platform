import sqlite3
import os
import time

db_path = "data/client_local.db"

def run_sql(sql):
    print(f"Executing: {sql}")
    conn = sqlite3.connect(db_path, timeout=5)
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        print("Success!")
    except sqlite3.OperationalError as e:
        print(f"OperationalError: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    if not os.path.exists(db_path):
        print("DB not found")
    else:
        # Add column
        run_sql("ALTER TABLE flowregistry ADD COLUMN trigger_id INTEGER")
        # Add index
        run_sql("CREATE INDEX ix_flowregistry_trigger_id ON flowregistry (trigger_id)")
        
        # Verify
        print("\n--- Verification ---")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(flowregistry)")
        for col in cursor.fetchall():
            print(col)
        conn.close()
