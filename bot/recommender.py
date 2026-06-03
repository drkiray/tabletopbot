def recommend_games(games, ratings, attendee_count, top_n=5):
    """
    games: list of game dicts (id, name, min_players, max_players, complexity)
    ratings: dict of {user_id: {game_id: like_score}}
    attendee_count: int
    Returns top_n games sorted by avg like score among attendees, filtered by player count.
    """
    eligible = [g for g in games if g["min_players"] <= attendee_count <= g["max_players"]]

    def avg_score(game):
        game_id = game["id"]
        scores = [
            user_ratings[game_id]
            for user_ratings in ratings.values()
            if game_id in user_ratings
        ]
        if not scores:
            return -1.0
        return sum(scores) / len(scores)

    ranked = sorted(eligible, key=avg_score, reverse=True)
    return ranked[:top_n]
