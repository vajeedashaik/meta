from __future__ import annotations

import json
import os
from typing import List, Optional

from viral_script_engine.memory.creator_history import CreatorHistoryBuffer


class HistoryStore:
    """
    Persists CreatorHistoryBuffers to disk, one JSON file per creator.
    """

    def __init__(self, store_dir: str = "data/creator_histories"):
        os.makedirs(store_dir, exist_ok=True)
        self.store_dir = store_dir

    def load(self, creator_id: str) -> Optional[CreatorHistoryBuffer]:
        path = os.path.join(self.store_dir, f"{creator_id}.json")
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return CreatorHistoryBuffer(**json.load(f))

    def save(self, buffer: CreatorHistoryBuffer) -> None:
        path = os.path.join(self.store_dir, f"{buffer.creator_id}.json")
        with open(path, "w") as f:
            json.dump(buffer.model_dump(), f, indent=2)

    def list_creators(self) -> List[str]:
        return [
            f.replace(".json", "")
            for f in os.listdir(self.store_dir)
            if f.endswith(".json")
        ]
