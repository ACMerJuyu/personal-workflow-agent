import json
from pathlib import Path
from typing import Any, Dict


class UserMemory:
    def __init__(self, path: str = "data/memory.json"):
        self.path = Path(path)

    def load(self) -> Dict[str, Any]:
        with self.path.open("r", encoding="utf-8") as file:
            return json.load(file)

