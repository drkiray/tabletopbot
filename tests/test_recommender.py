from bot.recommender import recommend_games

def make_game(id, name, min_p, max_p):
    return {"id": id, "name": name, "min_players": min_p, "max_players": max_p, "complexity": 5}

def test_filters_by_player_count():
    games = [
        make_game(1, "Маленькая", 2, 4),
        make_game(2, "Большая", 2, 8),
    ]
    ratings = {1: {1: 9, 2: 8}, 2: {1: 7, 2: 6}}
    result = recommend_games(games, ratings, attendee_count=6)
    names = [g["name"] for g in result]
    assert "Маленькая" not in names
    assert "Большая" in names

def test_ranks_by_average_like():
    games = [
        make_game(1, "Лучшая", 2, 6),
        make_game(2, "Средняя", 2, 6),
        make_game(3, "Худшая", 2, 6),
    ]
    ratings = {
        1: {1: 10, 2: 9, 3: 8},
        2: {1: 8,  2: 7, 3: 6},
    }
    result = recommend_games(games, ratings, attendee_count=3)
    assert result[0]["name"] == "Лучшая"
    assert result[1]["name"] == "Средняя"
    assert result[2]["name"] == "Худшая"

def test_returns_top_5():
    games = [make_game(i, f"Игра {i}", 2, 8) for i in range(1, 10)]
    ratings = {1: {i: 10 - i for i in range(1, 10)}}
    result = recommend_games(games, ratings, attendee_count=4)
    assert len(result) == 5

def test_games_with_no_ratings_included_last():
    games = [
        make_game(1, "Оценённая", 2, 6),
        make_game(2, "Неоценённая", 2, 6),
    ]
    ratings = {1: {1: 9}}
    result = recommend_games(games, ratings, attendee_count=3)
    assert result[0]["name"] == "Оценённая"
    assert result[1]["name"] == "Неоценённая"
