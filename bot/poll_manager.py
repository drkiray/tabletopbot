from collections import Counter

DAYS_ORDER = ["Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

def determine_winner(votes):
    """
    votes: list of vote dicts with 'day' key (only can_attend=1 votes)
    Returns winning day string or None if no votes.
    Tie-breaks by latest day in week.
    """
    if not votes:
        return None
    counts = Counter(v["day"] for v in votes)
    max_count = max(counts.values())
    top_days = [day for day, count in counts.items() if count == max_count]
    top_days.sort(key=lambda d: DAYS_ORDER.index(d) if d in DAYS_ORDER else -1, reverse=True)
    return top_days[0]
