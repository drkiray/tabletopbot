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
                like_score INTEGER NOT NULL CHECK(like_score BETWEEN 0 AND 10),
                complexity_score INTEGER CHECK(complexity_score BETWEEN 0 AND 10),
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

            CREATE TABLE IF NOT EXISTS session_games (
                poll_id INTEGER NOT NULL,
                game_id INTEGER NOT NULL,
                PRIMARY KEY (poll_id, game_id),
                FOREIGN KEY (poll_id) REFERENCES polls(id),
                FOREIGN KEY (game_id) REFERENCES games(id)
            );
        """)
        _migrate(conn)

def _migrate(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(ratings)").fetchall()]
    if "complexity_score" not in cols:
        conn.execute("ALTER TABLE ratings ADD COLUMN complexity_score INTEGER CHECK(complexity_score BETWEEN 0 AND 10)")
    poll_cols = [r[1] for r in conn.execute("PRAGMA table_info(polls)").fetchall()]
    if "poll_message_id" not in poll_cols:
        conn.execute("ALTER TABLE polls ADD COLUMN poll_message_id INTEGER")
    if "tracker_message_id" not in poll_cols:
        conn.execute("ALTER TABLE polls ADD COLUMN tracker_message_id INTEGER")
    if "attendance_tracker_message_id" not in poll_cols:
        conn.execute("ALTER TABLE polls ADD COLUMN attendance_tracker_message_id INTEGER")

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

def _merge_fake_user(conn, real_id, username):
    if not username:
        return
    fake = conn.execute(
        "SELECT id FROM users WHERE id < 0 AND LOWER(username) = LOWER(?)", (username,)
    ).fetchone()
    if not fake:
        return
    fake_id = fake[0]
    # Transfer historical ratings; real user's existing ratings take precedence
    conn.execute("""
        INSERT OR IGNORE INTO ratings (user_id, game_id, like_score, complexity_score)
        SELECT ?, game_id, like_score, complexity_score FROM ratings WHERE user_id = ?
    """, (real_id, fake_id))
    conn.execute("DELETE FROM ratings WHERE user_id = ?", (fake_id,))
    conn.execute("DELETE FROM votes WHERE user_id = ?", (fake_id,))
    conn.execute("DELETE FROM attendance WHERE user_id = ?", (fake_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (fake_id,))

def upsert_user(user_id, username, first_name, db_path=None):
    with _conn(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO users (id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username, first_name)
        )
        if user_id > 0:
            _merge_fake_user(conn, user_id, username)

def add_or_update_rating(user_id, game_id, like_score, db_path=None):
    with _conn(db_path) as conn:
        conn.execute(
            """INSERT INTO ratings (user_id, game_id, like_score)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id, game_id) DO UPDATE SET like_score = excluded.like_score""",
            (user_id, game_id, like_score)
        )

def add_or_update_rating_full(user_id, game_id, like_score, complexity_score, db_path=None):
    with _conn(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO ratings (user_id, game_id, like_score, complexity_score) VALUES (?, ?, ?, ?)",
            (user_id, game_id, like_score, complexity_score)
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
        cur = conn.execute(
            "UPDATE polls SET status = 'closed', chosen_day = ? WHERE id = ? AND status = 'open'",
            (chosen_day, poll_id)
        )
        return cur.rowcount > 0

def cancel_poll(poll_id, db_path=None):
    with _conn(db_path) as conn:
        cur = conn.execute(
            "UPDATE polls SET status = 'cancelled' WHERE id = ? AND status = 'open'", (poll_id,)
        )
        return cur.rowcount > 0

def record_vote(poll_id, user_id, day, can_attend, db_path=None):
    with _conn(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO votes (poll_id, user_id, day, can_attend) VALUES (?, ?, ?, ?)",
            (poll_id, user_id, day, 1 if can_attend else 0)
        )

def set_poll_message_ids(poll_id, poll_message_id, tracker_message_id, db_path=None):
    with _conn(db_path) as conn:
        conn.execute(
            "UPDATE polls SET poll_message_id = ?, tracker_message_id = ? WHERE id = ?",
            (poll_message_id, tracker_message_id, poll_id)
        )

def set_attendance_tracker_message_id(poll_id, message_id, db_path=None):
    with _conn(db_path) as conn:
        conn.execute(
            "UPDATE polls SET attendance_tracker_message_id = ? WHERE id = ?",
            (message_id, poll_id)
        )

def get_attendance_with_users(poll_id, db_path=None):
    with _conn(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT a.confirmed, u.username, u.first_name
            FROM attendance a
            JOIN users u ON a.user_id = u.id
            WHERE a.poll_id = ?
        """, (poll_id,)).fetchall()
        return [dict(r) for r in rows]

def get_votes_with_users(poll_id, db_path=None):
    with _conn(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT v.day, v.can_attend, v.user_id, u.username, u.first_name
            FROM votes v
            JOIN users u ON v.user_id = u.id
            WHERE v.poll_id = ?
        """, (poll_id,)).fetchall()
        return [dict(r) for r in rows]

def get_votes_for_poll(poll_id, db_path=None):
    with _conn(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM votes WHERE poll_id = ? AND can_attend = 1", (poll_id,)
        ).fetchall()
        return [dict(r) for r in rows]

def get_user_votes_for_poll(poll_id, user_id, db_path=None):
    with _conn(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT day, can_attend FROM votes WHERE poll_id = ? AND user_id = ?",
            (poll_id, user_id)
        ).fetchall()
        return {r["day"]: bool(r["can_attend"]) for r in rows}

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

def get_game_by_name_icase(name, db_path=None):
    with _conn(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM games WHERE LOWER(name) = LOWER(?)", (name,)
        ).fetchone()
        return dict(row) if row else None

def add_session_game(poll_id, game_id, db_path=None):
    with _conn(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO session_games (poll_id, game_id) VALUES (?,?)",
            (poll_id, game_id)
        )

def get_session_games(poll_id, db_path=None):
    with _conn(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT g.* FROM games g
               JOIN session_games sg ON g.id = sg.game_id
               WHERE sg.poll_id = ?
               ORDER BY g.name""",
            (poll_id,)
        ).fetchall()
        return [dict(r) for r in rows]

def get_ratings_summary(db_path=None):
    with _conn(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT g.name, ROUND(AVG(r.like_score), 1) AS avg_score, COUNT(r.user_id) AS num_ratings
            FROM games g
            LEFT JOIN ratings r ON g.id = r.game_id
            GROUP BY g.id
            ORDER BY avg_score DESC NULLS LAST, g.name
        """).fetchall()
        return [dict(r) for r in rows]

def get_game_ratings_detail(game_name, db_path=None):
    with _conn(db_path) as conn:
        conn.row_factory = sqlite3.Row
        game = conn.execute("SELECT * FROM games WHERE LOWER(name) = LOWER(?)", (game_name,)).fetchone()
        if not game:
            return None, []
        rows = conn.execute("""
            SELECT u.first_name, u.username, r.like_score, r.complexity_score
            FROM ratings r
            JOIN users u ON r.user_id = u.id
            WHERE r.game_id = ?
            ORDER BY r.like_score DESC
        """, (game["id"],)).fetchall()
        return dict(game), [dict(r) for r in rows]

def get_users_who_messaged_bot(db_path=None):
    with _conn(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id FROM users").fetchall()
        return [r["id"] for r in rows]

def get_user_by_username(username, db_path=None):
    username = username.lstrip("@")
    with _conn(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username,)
        ).fetchone()
        return dict(row) if row else None

def get_user_stats(user_id, db_path=None):
    with _conn(db_path) as conn:
        conn.row_factory = sqlite3.Row

        polls_voted = conn.execute(
            "SELECT COUNT(DISTINCT poll_id) FROM votes WHERE user_id = ?", (user_id,)
        ).fetchone()[0]

        positive_votes = conn.execute(
            "SELECT COUNT(*) FROM votes WHERE user_id = ? AND can_attend = 1", (user_id,)
        ).fetchone()[0]

        total_days_voted = conn.execute(
            "SELECT COUNT(*) FROM votes WHERE user_id = ?", (user_id,)
        ).fetchone()[0]

        confirmed = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE user_id = ? AND confirmed = 1", (user_id,)
        ).fetchone()[0]

        declined = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE user_id = ? AND confirmed = 0", (user_id,)
        ).fetchone()[0]

        games_rated = conn.execute(
            "SELECT COUNT(*) FROM ratings WHERE user_id = ?", (user_id,)
        ).fetchone()[0]

        fav_day_row = conn.execute(
            """SELECT day, COUNT(*) AS cnt FROM votes
               WHERE user_id = ? AND can_attend = 1
               GROUP BY day ORDER BY cnt DESC LIMIT 1""",
            (user_id,)
        ).fetchone()

        return {
            "polls_voted": polls_voted,
            "positive_votes": positive_votes,
            "total_days_voted": total_days_voted,
            "confirmed": confirmed,
            "declined": declined,
            "games_rated": games_rated,
            "fav_day": fav_day_row["day"] if fav_day_row else None,
        }

def get_all_users_stats(db_path=None):
    with _conn(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT u.id, u.username, u.first_name,
                   (SELECT COUNT(DISTINCT poll_id) FROM votes WHERE user_id = u.id) AS polls_voted,
                   (SELECT COUNT(*) FROM attendance WHERE user_id = u.id AND confirmed = 1) AS confirmed
            FROM users u
            WHERE u.id > 0
            ORDER BY confirmed DESC, polls_voted DESC
        """).fetchall()
        return [dict(r) for r in rows]

def get_user_top_games(user_id, limit=5, db_path=None):
    with _conn(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT g.name, r.like_score
            FROM ratings r
            JOIN games g ON r.game_id = g.id
            WHERE r.user_id = ? AND r.like_score IS NOT NULL
            ORDER BY r.like_score DESC
            LIMIT ?
        """, (user_id, limit)).fetchall()
        return [dict(r) for r in rows]
