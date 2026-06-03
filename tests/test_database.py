import os
import pytest
from bot.database import init_db, add_game, get_game, add_or_update_rating, get_ratings_for_game

TEST_DB = "test_tabletop.db"

@pytest.fixture(autouse=True)
def setup_db():
    init_db(TEST_DB)
    yield
    os.remove(TEST_DB)

def test_add_and_get_game():
    add_game("Каркассон", min_players=2, max_players=5, complexity=4, db_path=TEST_DB)
    game = get_game("Каркассон", db_path=TEST_DB)
    assert game["name"] == "Каркассон"
    assert game["min_players"] == 2
    assert game["max_players"] == 5
    assert game["complexity"] == 4

def test_add_and_get_rating():
    add_game("Каркассон", min_players=2, max_players=5, complexity=4, db_path=TEST_DB)
    game = get_game("Каркассон", db_path=TEST_DB)
    add_or_update_rating(user_id=111, game_id=game["id"], like_score=8, db_path=TEST_DB)
    ratings = get_ratings_for_game(game["id"], db_path=TEST_DB)
    assert len(ratings) == 1
    assert ratings[0]["like_score"] == 8

def test_update_rating():
    add_game("Каркассон", min_players=2, max_players=5, complexity=4, db_path=TEST_DB)
    game = get_game("Каркассон", db_path=TEST_DB)
    add_or_update_rating(user_id=111, game_id=game["id"], like_score=8, db_path=TEST_DB)
    add_or_update_rating(user_id=111, game_id=game["id"], like_score=10, db_path=TEST_DB)
    ratings = get_ratings_for_game(game["id"], db_path=TEST_DB)
    assert len(ratings) == 1
    assert ratings[0]["like_score"] == 10
