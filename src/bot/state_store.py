from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict

@dataclass
class SearchState:
    city: str = "Sokcho"
    checkin: str = "2026-03-10"   # YYYY-MM-DD
    checkout: str = "2026-03-12"
    adults: int = 2
    children: int = 0
    rooms: int = 1
    min_total_price: int = 0
    max_total_price: int = 220000
    min_rating: float = 8.0
    require_free_cancel: bool = False
    last_run: str = ""

class StateStore:
    def __init__(self, path: str = "data/search_state.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> SearchState:
        if not self.path.exists():
            return SearchState()
        data: Dict[str, Any] = json.loads(self.path.read_text(encoding="utf-8-sig"))
        s = SearchState()
        for k, v in data.items():
            if hasattr(s, k):
                setattr(s, k, v)
        return s

    def save(self, state: SearchState) -> None:
        self.path.write_text(
            json.dumps(asdict(state), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
