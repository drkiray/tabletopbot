import os
import pytest
from bot.database import init_db, create_poll, record_vote, get_votes_for_poll
from bot.poll_manager import determine_winner

TEST_DB = "test_poll.db"

@pytest.fixture(autouse=True)
def setup_db():
    init_db(TEST_DB)
    yield
    os.remove(TEST_DB)

def test_winner_is_most_votes():
    poll_id = create_poll("2026-06-01", db_path=TEST_DB)
    record_vote(poll_id, 1, "Суббота", True, db_path=TEST_DB)
    record_vote(poll_id, 2, "Суббота", True, db_path=TEST_DB)
    record_vote(poll_id, 3, "Воскресенье", True, db_path=TEST_DB)
    votes = get_votes_for_poll(poll_id, db_path=TEST_DB)
    assert determine_winner(votes) == "Суббота"

def test_tie_prefers_later_day():
    poll_id = create_poll("2026-06-01", db_path=TEST_DB)
    record_vote(poll_id, 1, "Суббота", True, db_path=TEST_DB)
    record_vote(poll_id, 2, "Воскресенье", True, db_path=TEST_DB)
    votes = get_votes_for_poll(poll_id, db_path=TEST_DB)
    assert determine_winner(votes) == "Воскресенье"

def test_no_votes_returns_none():
    assert determine_winner([]) is None
