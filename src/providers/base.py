from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Protocol, List

@dataclass(frozen=True)
class Listing:
    provider: str
    id: str
    title: str
    url: str
    price_total: Optional[int] = None
    rating: Optional[float] = None
    reviews: Optional[int] = None
    free_cancel: Optional[bool] = None
    location_text: Optional[str] = None

class Provider(Protocol):
    name: str
    async def fetch(self, url: str) -> List[Listing]:
        ...
