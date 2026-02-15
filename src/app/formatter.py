from __future__ import annotations
from src.providers.base import Listing

def format_msg(x: Listing) -> str:
    price = "-" if x.price_total is None else f"₩{x.price_total:,}"
    rating = "-" if x.rating is None else f"{x.rating}"
    reviews = "-" if x.reviews is None else str(x.reviews)
    cancel = "모름" if x.free_cancel is None else ("무료취소 ✅" if x.free_cancel else "무료취소 ❌")
    loc = "" if not x.location_text else f"\n📍 {x.location_text}"

    return (
        f"🏨 [{x.provider}] {x.title}\n"
        f"💰 총액: {price}\n"
        f"⭐ 평점: {rating} (후기 {reviews})\n"
        f"🧾 {cancel}{loc}\n"
        f"🔗 {x.url}"
    )
