def recommend_games(games, ratings, attendee_count, attendee_ids=None, top_n=5):
    """
    Returns list of (game, reason_str) tuples.

    If attendee_ids provided: priority = coverage (desc) → avg_like (desc) → lower complexity.
    Otherwise: fallback to avg_like across all ratings.
    """
    eligible = [g for g in games if g["min_players"] <= attendee_count <= g["max_players"]]

    def score_game(game):
        game_id = game["id"]
        if attendee_ids:
            raters = [uid for uid in attendee_ids if uid in ratings and game_id in ratings[uid]]
            coverage = len(raters)
            avg_like = (sum(ratings[uid][game_id] for uid in raters) / coverage) if raters else 0.0
        else:
            scores = [r[game_id] for r in ratings.values() if game_id in r]
            coverage = len(scores)
            avg_like = (sum(scores) / coverage) if scores else 0.0
        return (coverage, avg_like, -game["complexity"])

    def build_reason(game, score):
        coverage, avg_like, _ = score
        if attendee_ids:
            n = len(attendee_ids)
            if coverage == 0:
                return "никто из группы ещё не играл"
            elif coverage == n:
                return f"все играли, средний балл {avg_like:.1f}/10"
            else:
                return f"{coverage} из {n} играли, средний балл {avg_like:.1f}/10"
        else:
            if avg_like == 0.0:
                return "нет оценок"
            return f"средняя оценка {avg_like:.1f}/10 ({coverage} чел.)"

    scored = [(g, score_game(g)) for g in eligible]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [(g, build_reason(g, s)) for g, s in scored[:top_n]]
