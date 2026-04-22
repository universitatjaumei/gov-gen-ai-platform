import sqlite3
import os

db_path = "data/client_local.db"
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("--- Tables ---")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        for table in cursor.fetchall():
            print(table[0])
            
        print("\n--- flowregistry Schema ---")
        cursor.execute("PRAGMA table_info(flowregistry)")
        for col in cursor.fetchall():
            print(col)
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
