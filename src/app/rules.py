from __future__ import annotations
from dataclasses import dataclass
from src.providers.base import Listing

@dataclass(frozen=True)
class Rules:
    min_total_price: int
    max_total_price: int
    min_rating: float
    require_free_cancel: bool

def match_rules(x: Listing, rules: Rules) -> bool:
    # 가격 범위 조건
    if x.price_total is not None:
        if x.price_total < rules.min_total_price:
            return False
        if x.price_total > rules.max_total_price:
            return False

    # 평점 조건
    if x.rating is not None and x.rating < rules.min_rating:
        return False

    # 무료취소 조건
    if rules.require_free_cancel and x.free_cancel is False:
        return False

    return True
