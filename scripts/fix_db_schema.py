#!/usr/bin/env python3
"""One-time migration: fix ratings CHECK constraint from BETWEEN 1 AND 10 to BETWEEN 0 AND 10."""
import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "/opt/tabletop_bot/tabletop.db")
conn = sqlite3.connect(DB_PATH)

row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='ratings'").fetchone()
if not row:
    print("Table 'ratings' not found — nothing to fix.")
    conn.close()
    exit(0)

print("Current schema:", row[0])

if "BETWEEN 1 AND 10" not in row[0]:
    print("Constraint is already correct.")
    conn.close()
    exit(0)

print("Fixing constraint...")
conn.executescript("""
    CREATE TABLE ratings_new (
        user_id INTEGER NOT NULL,
        game_id INTEGER NOT NULL,
        like_score INTEGER NOT NULL CHECK(like_score BETWEEN 0 AND 10),
        PRIMARY KEY (user_id, game_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (game_id) REFERENCES games(id)
    );
    INSERT OR IGNORE INTO ratings_new SELECT * FROM ratings;
    DROP TABLE ratings;
    ALTER TABLE ratings_new RENAME TO ratings;
""")
conn.commit()
new_schema = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='ratings'").fetchone()[0]
print("Fixed schema:", new_schema)
conn.close()
print("Done!")
