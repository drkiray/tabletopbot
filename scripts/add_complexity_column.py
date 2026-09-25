import sqlite3, os
conn = sqlite3.connect(os.environ["DB_PATH"])
cols = [r[1] for r in conn.execute("PRAGMA table_info(ratings)").fetchall()]
if "complexity_score" in cols:
    print("Column already exists.")
else:
    conn.execute("ALTER TABLE ratings ADD COLUMN complexity_score INTEGER CHECK(complexity_score BETWEEN 0 AND 10)")
    conn.commit()
    print("Column added.")
conn.close()
