import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.storage import SQLiteStorage


def main():
    storage = SQLiteStorage()
    storage.seed_from_json(force=True)
    print(f"Initialized SQLite database at {storage.db_path}")


if __name__ == "__main__":
    main()
