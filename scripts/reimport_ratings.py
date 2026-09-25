#!/usr/bin/env python3
"""
Re-import ratings from Google Sheets with correct data.
Clears all fake-user (negative ID) ratings and re-inserts correct values.

Run on server:
  cd /opt/tabletop_bot && source .env && .venv/bin/python -m scripts.reimport_ratings
"""

import sqlite3
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.environ.get("DB_PATH", "/opt/tabletop_bot/tabletop.db")

# Fake user IDs for historical players (negative to avoid collision with real Telegram IDs)
PLAYERS = [
    (-1,  "drkiray",       "@drkiray"),        # 0
    (-2,  "Vasilyy",       "@Vasilyy"),        # 1
    (-3,  "stunz8",        "@stunz8"),         # 2
    (-4,  "Estarel",       "@Estarel"),        # 3
    (-5,  "RDMgreen",      "@RDMgreen"),       # 4
    (-6,  "ohmyroxy",      "@ohmyroxy"),       # 5
    (-7,  "Evaargonova",   "@Evaargonova"),    # 6
    (-8,  "Creskiv",       "@Creskiv"),        # 7
    (-9,  "SingFire",      "@SingFire"),       # 8
    (-10, "nikitosfrolov", "@nikitosfrolov"),  # 9
    (-11, "nepopus",       "@nepopus"),        # 10
    (-12, "im_6C697269",   "@im_6C697269"),    # 11
    (-13, "chiglik",       "chiglik"),         # 12
]

# Each entry: (game_name, min_players, max_players, ratings)
# ratings: list of (player_index, like_score, complexity_score_or_None)
# Player indices match PLAYERS list above (0=drkiray, 1=Vasilyy, etc.)
GAMES = [
    ("7 чудес", 3, 7, [
        (0,  8, 1),    # drkiray
        (1,  7, None), # Vasilyy
        (4,  8, 3),    # rdmgreen
        (6,  7, None), # Evaargonova
        (7,  7, 4),    # Creskiv
        (8,  6, 2),    # SingFire
        (10, 8, 8),    # nepopus
    ]),
    ("Алхимики", 2, 6, [
        (0,  8, 5),    # drkiray
        (7,  8, 6),    # Creskiv
        (10, 8, 8),    # nepopus
    ]),
    ("Битва боевых магов", 2, 6, [
        (0,  9, 2),    # drkiray
        (4,  8, 3),    # rdmgreen
        (7,  8, 2),    # Creskiv
        (8,  5, 1),    # SingFire
        (10, 9, 8),    # nepopus
    ]),
    ("Ваальбара", 2, 4, [
        (0,  8, 2),    # drkiray
        (2,  3, 4),    # stunz8
        (4,  8, 4),    # rdmgreen
        (10, 8, 8),    # nepopus
    ]),
    ("Ведьмин Круг", 2, 5, [
        (0,  8, 3),    # drkiray
    ]),
    ("Взрывные котята", 2, 5, [
        (0,  7, 2),    # drkiray
        (2,  7, 2),    # stunz8
        (3,  5, 3),    # Estarel
        (4,  5, 1),    # rdmgreen
        (5,  6, None), # ohmyroxy
        (6,  7, None), # Evaargonova
        (8,  2, 0),    # SingFire
        (10, 7, 8),    # nepopus
    ]),
    ("Войны Чёрной Розы: Возрождение", 2, 4, [
        (0,  8, 8),    # drkiray
        (1,  5, 7),    # Vasilyy
        (2,  5, None), # stunz8
        (3,  8, 9),    # Estarel
        (4,  9, 8),    # rdmgreen
        (6,  8, None), # Evaargonova
        (8,  8, 8),    # SingFire
        (10, 8, 8),    # nepopus
    ]),
    ("Глубокие печали", 2, 5, [
        (2,  7, 4),    # stunz8
        (4,  7, 4),    # rdmgreen
    ]),
    ("Голоса в голове", 2, 6, [
        (0,  7, 4),    # drkiray
        (2,  5, 5),    # stunz8
        (4,  6, 4),    # rdmgreen
        (10, 7, 8),    # nepopus
    ]),
    ("Дорога ярости", 2, 5, [
        (0,  9, 3),    # drkiray
        (2,  9, 2),    # stunz8
        (3,  8, 4),    # Estarel
        (4,  8, 2),    # rdmgreen
        (8,  7, 3),    # SingFire
        (10, 9, 8),    # nepopus
    ]),
    ("Дюна Империи", 2, 6, [
        (0,  9, 6),    # drkiray
        (2,  6, 8),    # stunz8
        (3,  9, 9),    # Estarel
        (4,  9, 6),    # rdmgreen
        (8,  8, 7),    # SingFire
        (10, 9, 8),    # nepopus
    ]),
    ("За Бортом", 2, 6, [
        (0,  7, 3),    # drkiray
        (4,  3, 2),    # rdmgreen
        (7,  6, 3),    # Creskiv
        (8,  6, 0),    # SingFire
        (10, 7, 8),    # nepopus
    ]),
    ("Замес Манчкин", 2, 6, [
        (0,  8, 2),    # drkiray
        (4,  1, 1),    # rdmgreen
        (5,  7, None), # ohmyroxy
        (6,  8, None), # Evaargonova
        (8,  5, 2),    # SingFire
        (10, 8, 8),    # nepopus
    ]),
    ("Звёздные войны: Imperial assault", 2, 5, [
        (4,  8, 5),    # rdmgreen
    ]),
    ("Звездные империи", 2, 4, [
        (0,  8, 3),    # drkiray
        (2,  6, 4),    # stunz8
        (4,  5, 5),    # rdmgreen
    ]),
    ("Инновация", 2, 4, [
        (0,  8, 3),    # drkiray
        (10, 8, 8),    # nepopus
    ]),
    ("Каркассон", 2, 5, [
        (0,  9, 2),    # drkiray
        (3,  6, 3),    # Estarel
        (4,  4, 1),    # rdmgreen
        (7,  8, 2),    # Creskiv
        (8,  5, 2),    # SingFire
        (10, 9, 8),    # nepopus
        (11, 3, 6),    # im_6C697269
    ]),
    ("Коза Ностра", 2, 6, [
        (0,  9, 4),    # drkiray
        (1,  6, None), # Vasilyy
        (4,  7, 6),    # rdmgreen
        (8,  7, 3),    # SingFire
        (10, 9, 8),    # nepopus
    ]),
    ("Космический контакт", 2, 6, [
        (0,  10, 6),   # drkiray
        (1,  7, None), # Vasilyy
        (2,  8, 7),    # stunz8
        (3,  8, 5),    # Estarel
        (4,  10, 4),   # rdmgreen
        (6,  8, None), # Evaargonova
        (8,  8, 4),    # SingFire
        (10, 10, 8),   # nepopus
    ]),
    ("Крагморта", 2, 6, [
        (0,  5, 4),    # drkiray
        (1,  4, 0),    # Vasilyy
        (2,  6, 2),    # stunz8
        (7,  1, 0),    # Creskiv
        (10, 8, 8),    # nepopus
        (12, 8, 6),    # chiglik
    ]),
    ("Ктулху смерть может умереть", 2, 6, [
        (0,  6, 7),    # drkiray
        (1,  8, None), # Vasilyy
        (4,  8, 2),    # rdmgreen
        (6,  8, None), # Evaargonova
        (10, 6, 8),    # nepopus
    ]),
    ("Марвел Злодеи", 2, 5, [
        (0,  8, 7),    # drkiray
        (1,  6, None), # Vasilyy
        (2,  1, None), # stunz8
        (4,  6, 7),    # rdmgreen
        (6,  9, None), # Evaargonova
        (10, 8, 8),    # nepopus
    ]),
    ("Мачи Коро 2", 2, 5, [
        (0,  7, 2),    # drkiray
        (1,  6, None), # Vasilyy
        (4,  6, 3),    # rdmgreen
        (7,  6, 3),    # Creskiv
        (10, 7, 8),    # nepopus
    ]),
    ("Море, Соль, Бумага", 2, 6, [
        (0,  8, 1),    # drkiray
        (1,  6, None), # Vasilyy
        (2,  2, 3),    # stunz8
        (4,  4, 6),    # rdmgreen
        (10, 8, 8),    # nepopus
    ]),
    ("Неудержимые единорожки", 2, 8, [
        (0,  5, 0),    # drkiray
        (4,  5, 1),    # rdmgreen
        (5,  7, None), # ohmyroxy
        (6,  6, None), # Evaargonova
        (8,  2, 0),    # SingFire
        (10, 5, 8),    # nepopus
    ]),
    ("Нечто", 4, 8, [
        (0,  9, 2),    # drkiray
        (1,  8, None), # Vasilyy
        (4,  4, 3),    # rdmgreen
        (6,  7, None), # Evaargonova
        (8,  6, 3),    # SingFire
        (10, 9, 8),    # nepopus
    ]),
    ("Объяснярий (18+)", 4, 8, [
        (0,  5, 1),    # drkiray
        (2,  8, 2),    # stunz8
        (4,  5, 2),    # rdmgreen
    ]),
    ("Опасные гости", 3, 6, [
        (0,  6, 3),    # drkiray
        (3,  7, 6),    # Estarel
        (4,  5, 3),    # rdmgreen
        (6,  6, None), # Evaargonova
        (10, 6, 8),    # nepopus
    ]),
    ("Паника на Вулф-стрит", 3, 6, [
        (0,  8, 4),    # drkiray
        (1,  5, 5),    # Vasilyy
        (2,  5, 4),    # stunz8
        (7,  2, 3),    # Creskiv
        (10, 8, 8),    # nepopus
        (12, 8, 4),    # chiglik
    ]),
    ("Повелитель Токио", 2, 6, [
        (0,  9, 4),    # drkiray
        (1,  8, 2),    # Vasilyy
        (2,  7, 4),    # stunz8
        (3,  8, 1),    # Estarel
        (4,  7, 1),    # rdmgreen
        (6,  9, None), # Evaargonova
        (7,  4, 4),    # Creskiv
        (10, 9, 8),    # nepopus
        (12, 5, 9),    # chiglik
    ]),
    ("Призрачные чернила", 2, 6, [
        (0,  6, 1),    # drkiray
        (1,  7, 1),    # Vasilyy
        (2,  7, 3),    # stunz8
        (7,  7, 3),    # Creskiv
        (10, 8, 8),    # nepopus
        (12, 7, 6),    # chiglik
    ]),
    ("Проект Элита", 1, 4, [
        (0,  10, 6),   # drkiray
        (1,  9, None), # Vasilyy
        (4,  8, 3),    # rdmgreen
        (6,  9, None), # Evaargonova
        (8,  9, 5),    # SingFire
        (10, 10, 8),   # nepopus
    ]),
    ("Сетка - игра для нетворкинга", 2, 8, [
        (0,  6, 1),    # drkiray
    ]),
    ("Тако, кот, коза, сыр, пицца", 2, 8, [
        (0,  7, 0),    # drkiray
        (1,  0, 1),    # Vasilyy
        (2,  0, 9),    # stunz8
        (3,  1, 10),   # Estarel
        (4,  5, 1),    # rdmgreen
        (6,  7, None), # Evaargonova
        (8,  1, 1),    # SingFire
        (10, 7, 8),    # nepopus
    ]),
    ("Ужас Аркхэма 3 ред.", 1, 8, [
        (0,  7, 6),    # drkiray
        (1,  8, None), # Vasilyy
        (2,  8, None), # stunz8
        (3,  9, 6),    # Estarel
        (4,  9, 4),    # rdmgreen
        (5,  8, None), # ohmyroxy
        (8,  7, 4),    # SingFire
        (10, 7, 8),    # nepopus
    ]),
    ("Ужас Аркхэма карточная игра", 1, 4, [
        (0,  8, 6),    # drkiray
        (4,  9, 4),    # rdmgreen
        (7,  9, 7),    # Creskiv
        (10, 8, 8),    # nepopus
    ]),
    ("Цитадели", 2, 8, [
        (0,  9, 3),    # drkiray
        (3,  7, 4),    # Estarel
        (4,  7, 3),    # rdmgreen
        (6,  7, None), # Evaargonova
        (7,  8, 3),    # Creskiv
        (8,  6, 3),    # SingFire
        (10, 9, 8),    # nepopus
    ]),
    ("Шериф Нотингема", 3, 6, [
        (0,  9, 4),    # drkiray
        (2,  3, 5),    # stunz8
        (3,  7, 3),    # Estarel
        (4,  6, 2),    # rdmgreen
        (6,  6, None), # Evaargonova
        (10, 9, 8),    # nepopus
    ]),
    ("Энергосеть", 2, 6, [
        (4,  5, 3),    # rdmgreen
        (10, 6, 8),    # nepopus
    ]),
    ("Это бомба!", 2, 5, [
        (0,  8, 1),    # drkiray
        (4,  9, 1),    # rdmgreen
        (10, 8, 8),    # nepopus
    ]),
    ("Arcs - Предел: Раздор и падение", 2, 4, [
        (0,  9, 7),    # drkiray
        (4,  6, 6),    # rdmgreen
        (10, 9, 8),    # nepopus
    ]),
    ("Codenames", 4, 8, [
        (0,  6, 1),    # drkiray
        (3,  8, 4),    # Estarel
        (4,  5, 2),    # rdmgreen
        (7,  6, 1),    # Creskiv
        (8,  7, 2),    # SingFire
        (10, 6, 8),    # nepopus
    ]),
    ("Dead Cells", 2, 4, [
        (0,  8, 6),    # drkiray
        (4,  9, 2),    # rdmgreen
        (10, 8, 8),    # nepopus
    ]),
    ("Fuse", 2, 5, [
        (0,  9, 2),    # drkiray
        (3,  7, 3),    # Estarel
        (4,  10, 2),   # rdmgreen
        (10, 9, 8),    # nepopus
    ]),
    ("Long Shot", 2, 8, [
        (0,  8, 4),    # drkiray
        (1,  7, 5),    # Vasilyy
        (2,  0, 5),    # stunz8
        (3,  8, 2),    # Estarel
        (4,  8, 2),    # rdmgreen
        (6,  8, None), # Evaargonova
        (7,  3, 5),    # Creskiv
        (10, 8, 8),    # nepopus
        (12, 4, 4),    # chiglik
    ]),
    ("MTG Archenemy + Planechase", 3, 6, [
        (0,  10, 8),   # drkiray
        (2,  2,  9),   # stunz8
        (3,  10, 10),  # Estarel
        (4,  2,  10),  # rdmgreen
        (7,  5,  10),  # Creskiv
        (8,  7,  10),  # SingFire
        (10, 10, 8),   # nepopus
        (11, 6,  8),   # im_6C697269
    ]),
    ("Oathsworn: Верные клятве", 1, 4, [
        (0,  6, 8),    # drkiray
        (2,  8, 6),    # stunz8
        (3,  9, 5),    # Estarel
        (4,  10, 6),   # rdmgreen
        (10, 6, 8),    # nepopus
    ]),
    ("Primal", 1, 4, [
        (0,  7, 6),    # drkiray
        (4,  10, 8),   # rdmgreen
    ]),
    ("Similo: Животные", 2, 8, [
        (0,  5, 0),    # drkiray
        (1,  0, 0),    # Vasilyy
        (2,  0, 2),    # stunz8
        (4,  5, 1),    # rdmgreen
        (10, 5, 8),    # nepopus
    ]),
    ("Sunderfolk", 2, 4, [
        (4,  8, 4),    # rdmgreen
    ]),
    ("Ticket to Ride", 2, 5, [
        (0,  8, 4),    # drkiray
        (3,  7, 4),    # Estarel
        (4,  5, 3),    # rdmgreen
        (5,  7, None), # ohmyroxy
        (6,  7, None), # Evaargonova
        (7,  8, 3),    # Creskiv
    ]),
    ("Vantage", 2, 4, [
        (0,  9, 5),    # drkiray
        (1,  9, 3),    # Vasilyy
        (4,  9, 2),    # rdmgreen
    ]),
]


def reimport_ratings():
    conn = sqlite3.connect(DB_PATH)
    print(f"База данных: {DB_PATH}")

    # Ensure fake users exist
    for uid, username, first_name in PLAYERS:
        conn.execute(
            "INSERT OR IGNORE INTO users (id, username, first_name) VALUES (?,?,?)",
            (uid, username, first_name)
        )
    print(f"Игроки: {len(PLAYERS)}")

    # Clear all fake-user ratings
    deleted = conn.execute("DELETE FROM ratings WHERE user_id < 0").rowcount
    print(f"Удалено старых оценок: {deleted}")

    ratings_added = 0
    missing_games = []

    for name, min_p, max_p, player_ratings in GAMES:
        # Insert game if not exists (don't overwrite existing settings)
        conn.execute(
            "INSERT OR IGNORE INTO games (name, min_players, max_players, complexity) VALUES (?,?,?,5)",
            (name, min_p, max_p)
        )
        game_row = conn.execute("SELECT id FROM games WHERE name=?", (name,)).fetchone()
        if not game_row:
            missing_games.append(name)
            continue
        game_id = game_row[0]

        for player_idx, heart, skull in player_ratings:
            uid = PLAYERS[player_idx][0]
            conn.execute(
                "INSERT OR REPLACE INTO ratings (user_id, game_id, like_score, complexity_score) "
                "VALUES (?,?,?,?)",
                (uid, game_id, heart, skull)
            )
            ratings_added += 1

    conn.commit()
    conn.close()

    print(f"Оценок добавлено: {ratings_added}")
    if missing_games:
        print(f"Игры не найдены в БД: {missing_games}")
    print("Готово!")


if __name__ == "__main__":
    reimport_ratings()
