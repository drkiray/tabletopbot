#!/usr/bin/env python3
"""
Import games and player ratings from the "Настолки у Ярика" Google Sheet.

Run on server:
  cd /opt/tabletop_bot && .venv/bin/python -m scripts.import_from_sheets
"""

import sqlite3
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.environ.get("DB_PATH", "/opt/tabletop_bot/tabletop.db")

# Fake user IDs for historical players (negative to avoid collision with real Telegram IDs)
# Format: (fake_id, username, display_name)
PLAYERS = [
    (-1,  "drkiray",       "@drkiray"),
    (-2,  "Vasilyy",       "@Vasilyy"),
    (-3,  "stunz8",        "@stunz8"),
    (-4,  "Estarel",       "@Estarel"),
    (-5,  "RDMgreen",      "@RDMgreen"),
    (-6,  "ohmyroxy",      "@ohmyroxy"),
    (-7,  "Evaargonova",   "@Evaargonova"),
    (-8,  "Creskiv",       "@Creskiv"),
    (-9,  "SingFire",      "@SingFire"),
    (-10, "nikitosfrolov", "@nikitosfrolov"),
    (-11, "nepopus",       "@nepopus"),
    (-12, "im_6C697269",   "@im_6C697269"),
    (-13, "chiglik",       "chiglik"),
]

# Data from spreadsheet.
# Format per row: [name, avg_heart, avg_skull, p1_heart, p1_skull, p2_heart, p2_skull, ...]
# Players in order: drkiray, Vasilyy, stunz8, Estarel, Илья, ohmyroxy, Eva argo,
#                   Creskiv, SingFire, nikitosfrolov, nepopus, Liri, chiglik
# min_players/max_players set to reasonable defaults; update via /add_game if needed
GAMES = [
    # name,                                      min, max, data...
    ("7 чудес",                                   3,   7,  "7,3,3,6,8,1,7,8,3,7,7,4,6,2,8,8"),
    ("Алхимики",                                  2,   6,  "8,0,6,3,8,5,8,6,8,8"),
    ("Битва боевых магов",                        2,   6,  "7,8,3,2,9,2,8,3,8,2,5,1,9,8"),
    ("Ваальбара",                                 2,   4,  "6,8,4,5,8,2,3,4,8,4,8,8"),
    ("Ведьмин Круг",                              2,   5,  "8,0,3,0,8,3"),
    ("Взрывные котята",                           2,   5,  "5,8,2,7,7,2,7,2,5,3,5,1,6,7,2,0,7,8"),
    ("Войны Чёрной Розы: Возрождение",            2,   4,  "7,4,8,0,8,8,5,7,5,8,9,9,8,8,8,8,8,8"),
    ("Глубокие печали",                           2,   5,  "7,0,4,0,7,4,7,4"),
    ("Голоса в голове",                           2,   6,  "6,3,5,3,7,4,5,5,6,4,7,8"),
    ("Дорога ярости",                             2,   5,  "8,3,3,7,9,3,9,2,8,4,8,2,7,3,9,8"),
    ("Дюна Империи",                              2,   6,  "8,3,7,3,9,6,6,8,9,9,9,6,8,7,9,8"),
    ("За Бортом",                                 2,   6,  "5,8,3,2,7,3,3,2,6,3,6,0,7,8"),
    ("Замес Манчкин",                             2,   6,  "6,2,3,3,8,2,1,1,7,8,5,2,8,8"),
    ("Звёздные войны: Imperial assault",           2,   5,  "8,0,5,0,8,5"),
    ("Звездные империи",                          2,   4,  "6,3,4,0,8,3,6,4,5,5"),
    ("Инновация",                                 2,   4,  "8,0,5,5,8,3,8,8"),
    ("Каркассон",                                 2,   5,  "6,3,3,4,9,2,6,3,4,1,8,2,5,2,9,8,3,6"),
    ("Коза Ностра",                               2,   6,  "7,6,5,3,9,4,6,7,6,7,3,9,8"),
    ("Космический контакт",                       2,   6,  "8,6,5,7,10,6,7,8,7,8,5,10,4,8,8,4,10,8"),
    ("Крагморта",                                 2,   6,  "5,3,3,3,5,4,4,0,6,2,1,0,8,8,8,6"),
    ("Ктулху смерть может умереть",               2,   6,  "7,2,5,7,6,7,8,8,2,8,6,8"),
    ("Марвел Злодеи",                             2,   5,  "6,3,7,3,8,7,6,1,6,7,9,8,8"),
    ("Мачи Коро 2",                               2,   5,  "6,4,4,0,7,2,6,6,3,6,3,7,8"),
    ("Море, Соль, Бумага",                        2,   6,  "5,6,4,5,8,1,6,2,3,4,6,8,8"),
    ("Неудержимые единорожки",                    2,   8,  "5,0,2,3,5,0,5,1,7,6,2,0,5,8"),
    ("Нечто",                                     4,   8,  "7,2,4,0,9,2,8,4,3,7,6,3,9,8"),
    ("Объяснярий (18+)",                          4,   8,  "6,0,1,7,5,1,8,2,5,2"),
    ("Опасные гости",                             3,   6,  "6,0,5,0,6,3,7,6,5,3,6,6,8"),
    ("Паника на Вулф-стрит",                      3,   6,  "6,0,4,7,8,4,5,5,5,4,2,3,8,8,8,4"),
    ("Повелитель Токио",                          2,   6,  "7,3,4,1,9,4,8,2,7,4,8,1,7,1,9,4,4,9,8,5,9"),
    ("Призрачные чернила",                        2,   6,  "7,0,3,7,6,1,7,1,7,3,7,3,8,8,7,6"),
    ("Проект Элита",                              1,   4,  "9,2,5,5,10,6,9,8,3,9,9,5,10,8"),
    ("Сетка - игра для нетворкинга",             2,   8,  "6,0,1,0,6,1"),
    ("Тако, кот, коза, сыр, пицца",              2,   8,  "3,5,4,3,7,0,0,1,0,9,1,10,5,1,7,1,1,7,8"),
    ("Ужас Аркхэма 3 ред.",                       1,   8,  "7,9,5,6,7,6,8,8,9,6,9,4,8,7,4,7,8"),
    ("Ужас Аркхэма карточная игра",              1,   4,  "8,5,6,3,8,6,9,4,9,7,8,8"),
    ("Цитадели",                                  2,   8,  "7,6,4,0,9,3,7,4,7,3,7,8,3,6,3,9,8"),
    ("Шериф Нотингема",                           3,   6,  "6,7,4,4,9,4,3,5,7,3,6,2,6,9,8"),
    ("Энергосеть",                                2,   6,  "5,5,5,5,5,3,6,8"),
    ("Это бомба!",                                2,   5,  "8,3,3,3,8,1,9,1,8,8"),
    ("Arcs - Предел: Раздор и падение",           2,   4,  "8,0,7,0,9,7,6,6,9,8"),
    ("Codenames",                                 4,   8,  "6,3,3,0,6,1,8,4,5,2,6,1,7,2,6,8"),
    ("Dead Cells",                                2,   4,  "8,3,5,3,8,6,9,2,8,8"),
    ("Fuse",                                      2,   5,  "8,8,3,8,9,2,7,3,10,2,9,8"),
    ("Long Shot",                                 2,   8,  "6,0,4,4,8,4,7,5,0,5,8,2,8,2,8,3,5,8,8,4,4"),
    ("MTG Archenemy + Planechase",                3,   6,  "6,5,9,1,10,8,2,9,10,10,2,10,5,10,7,10,10,8,6,8"),
    ("Oathsworn: Верные клятве",                  1,   4,  "7,8,6,6,6,8,8,6,9,5,10,6,6,8"),
    ("Primal",                                    1,   4,  "8,5,7,0,7,6,10,8"),
    ("Similo: Животные",                          2,   8,  "3,0,2,2,5,0,0,0,0,2,5,1,5,8"),
    ("Sunderfolk",                                2,   4,  "8,0,4,0,8,4"),
    ("Ticket to Ride",                            2,   5,  "7,0,3,5,8,4,7,4,5,3,7,7,8,3"),
    ("Vantage",                                   2,   4,  "9,0,3,3,9,5,9,3,9,2"),
]


def import_data():
    conn = sqlite3.connect(DB_PATH)

    print(f"База данных: {DB_PATH}")

    # Insert placeholder users
    for uid, username, first_name in PLAYERS:
        conn.execute(
            "INSERT OR IGNORE INTO users (id, username, first_name) VALUES (?,?,?)",
            (uid, username, first_name)
        )
    print(f"Добавлено {len(PLAYERS)} игроков")

    games_added = 0
    ratings_added = 0

    for name, min_p, max_p, data_str in GAMES:
        values = [v.strip() for v in data_str.split(",")]
        # First two values are avg_heart and avg_skull (we use avg_skull as complexity)
        try:
            complexity = int(values[1]) if len(values) > 1 and values[1] else 5
        except ValueError:
            complexity = 5
        complexity = max(1, min(10, complexity))

        conn.execute(
            "INSERT OR IGNORE INTO games (name, min_players, max_players, complexity) VALUES (?,?,?,?)",
            (name, min_p, max_p, complexity)
        )
        game_row = conn.execute("SELECT id FROM games WHERE name=?", (name,)).fetchone()
        if not game_row:
            continue
        game_id = game_row[0]
        games_added += 1

        # Player ratings start at index 2 (after avg_heart and avg_skull)
        player_data = values[2:]
        for i, (uid, username, _) in enumerate(PLAYERS):
            heart_idx = i * 2
            skull_idx = i * 2 + 1
            if heart_idx >= len(player_data):
                break
            heart_str = player_data[heart_idx]
            skull_str = player_data[skull_idx] if skull_idx < len(player_data) else ""
            if not heart_str:
                continue
            try:
                heart = int(heart_str)
                skull = int(skull_str) if skull_str else None
                if skull is not None and not (0 <= skull <= 10):
                    skull = None
                if 0 <= heart <= 10:
                    conn.execute(
                        "INSERT OR REPLACE INTO ratings (user_id, game_id, like_score, complexity_score) VALUES (?,?,?,?)",
                        (uid, game_id, heart, skull)
                    )
                    ratings_added += 1
            except ValueError:
                pass

    conn.commit()
    conn.close()

    print(f"Игр добавлено: {games_added}")
    print(f"Оценок добавлено: {ratings_added}")
    print("Готово!")


if __name__ == "__main__":
    import_data()
