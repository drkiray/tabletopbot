import sqlite3
from bot.config import DB_PATH as DEFAULT_DB_PATH

def _conn(db_path=None):
    return sqlite3.connect(db_path or DEFAULT_DB_PATH)

def init_db(db_path=None):
    with _conn(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                min_players INTEGER NOT NULL,
                max_players INTEGER NOT NULL,
                complexity INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT
            );

            CREATE TABLE IF NOT EXISTS ratings (
                user_id INTEGER NOT NULL,
                game_id INTEGER NOT NULL,
                like_score INTEGER NOT NULL CHECK(like_score BETWEEN 1 AND 10),
                PRIMARY KEY (user_id, game_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (game_id) REFERENCES games(id)
            );

            CREATE TABLE IF NOT EXISTS polls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_start TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                chosen_day TEXT
            );

            CREATE TABLE IF NOT EXISTS votes (
                poll_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                day TEXT NOT NULL,
                can_attend INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (poll_id, user_id, day),
                FOREIGN KEY (poll_id) REFERENCES polls(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS attendance (
                poll_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                confirmed INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (poll_id, user_id),
                FOREIGN KEY (poll_id) REFERENCES polls(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)

def add_game(name, min_players, max_players, complexity, db_path=None):
    with _conn(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO games (name, min_players, max_players, complexity) VALUES (?, ?, ?, ?)",
            (name, min_players, max_players, complexity)
        )

def get_game(name, db_path=None):
    with _conn(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM games WHERE name = ?", (name,)).fetchone()
        return dict(row) if row else None

def get_game_by_id(game_id, db_path=None):
    with _conn(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
        return dict(row) if row else None

def get_all_games(db_path=None):
    with _conn(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM games ORDER BY name").fetchall()
        return [dict(r) for r in rows]

def delete_game(game_id, db_path=None):
    with _conn(db_path) as conn:
        conn.execute("DELETE FROM ratings WHERE game_id = ?", (game_id,))
        conn.execute("DELETE FROM games WHERE id = ?", (game_id,))

def upsert_user(user_id, username, first_name, db_path=None):
    with _conn(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO users (id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username, first_name)
        )

def add_or_update_rating(user_id, game_id, like_score, db_path=None):
    with _conn(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO ratings (user_id, game_id, like_score) VALUES (?, ?, ?)",
            (user_id, game_id, like_score)
        )

def get_ratings_for_game(game_id, db_path=None):
    with _conn(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM ratings WHERE game_id = ?", (game_id,)
        ).fetchall()
        return [dict(r) for r in rows]

def get_user_rating(user_id, game_id, db_path=None):
    with _conn(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM ratings WHERE user_id = ? AND game_id = ?",
            (user_id, game_id)
        ).fetchone()
        return dict(row) if row else None

def create_poll(week_start, db_path=None):
    with _conn(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO polls (week_start, status) VALUES (?, 'open')", (week_start,)
        )
        return cur.lastrowid

def get_open_poll(db_path=None):
    with _conn(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM polls WHERE status = 'open' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

def close_poll(poll_id, chosen_day, db_path=None):
    with _conn(db_path) as conn:
        conn.execute(
            "UPDATE polls SET status = 'closed', chosen_day = ? WHERE id = ?",
            (chosen_day, poll_id)
        )

def cancel_poll(poll_id, db_path=None):
    with _conn(db_path) as conn:
        conn.execute(
            "UPDATE polls SET status = 'cancelled' WHERE id = ?", (poll_id,)
        )

def record_vote(poll_id, user_id, day, can_attend, db_path=None):
    with _conn(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO votes (poll_id, user_id, day, can_attend) VALUES (?, ?, ?, ?)",
            (poll_id, user_id, day, 1 if can_attend else 0)
        )

def get_votes_for_poll(poll_id, db_path=None):
    with _conn(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM votes WHERE poll_id = ? AND can_attend = 1", (poll_id,)
        ).fetchall()
        return [dict(r) for r in rows]

def record_attendance(poll_id, user_id, confirmed, db_path=None):
    with _conn(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO attendance (poll_id, user_id, confirmed) VALUES (?, ?, ?)",
            (poll_id, user_id, 1 if confirmed else 0)
        )

def get_confirmed_attendees(poll_id, db_path=None):
    with _conn(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT user_id FROM attendance WHERE poll_id = ? AND confirmed = 1", (poll_id,)
        ).fetchall()
        return [r["user_id"] for r in rows]

def get_users_who_messaged_bot(db_path=None):
    with _conn(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id FROM users").fetchall()
        return [r["id"] for r in rows]
