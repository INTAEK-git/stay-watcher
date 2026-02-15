from __future__ import annotations
import json
from pathlib import Path

class SeenStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> set[str]:
        if not self.path.exists():
            return set()

        # 윈도우에서 저장된 UTF-8 BOM(서명)이 있어도 읽히도록 utf-8-sig 사용
        text = self.path.read_text(encoding="utf-8-sig").strip()
        if not text:
            return set()

        return set(json.loads(text))

    def save(self, seen: set[str]) -> None:
        # 저장은 BOM 없는 UTF-8로 저장 (ensure_ascii=False는 한글 안전)
        self.path.write_text(
            json.dumps(sorted(seen), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
