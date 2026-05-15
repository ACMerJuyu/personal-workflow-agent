import json
from pathlib import Path
from typing import Any, Dict, Optional

from agent.storage import SQLiteStorage


class UserMemory:
    def __init__(self, path: str = "data/memory.json", storage: Optional[SQLiteStorage] = None):
        self.path = Path(path)
        self.storage = storage

    def load(self) -> Dict[str, Any]:
        if self.storage:
            return self.storage.load_memory()

        with self.path.open("r", encoding="utf-8") as file:
            return json.load(file)
