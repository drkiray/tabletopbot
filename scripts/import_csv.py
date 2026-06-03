"""
One-time import of games from CSV.

CSV format:
  name,min_players,max_players,complexity

Run:
  python -m scripts.import_csv data/games.csv
"""
import csv
import sys
from bot.database import init_db, add_game

def import_games(csv_path):
    init_db()
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            add_game(
                name=row["name"].strip(),
                min_players=int(row["min_players"]),
                max_players=int(row["max_players"]),
                complexity=int(row["complexity"]),
            )
            count += 1
    print(f"Импортировано игр: {count}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python -m scripts.import_csv <path_to_csv>")
        sys.exit(1)
    import_games(sys.argv[1])
