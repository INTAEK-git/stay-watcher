from __future__ import annotations
import re
from typing import List, Optional
from urllib.parse import urljoin
from playwright.async_api import Page
from src.providers.base import Listing
from src.utils.playwright_pool import browser_context

def _to_int_price(text: str) -> Optional[int]:
    nums = re.findall(r"\d[\d,]*", text.replace(".", ""))
    if not nums:
        return None
    return int(nums[0].replace(",", ""))

def _to_float_rating(text: str) -> Optional[float]:
    m = re.search(r"(\d+(?:\.\d+)?)", text)
    return float(m.group(1)) if m else None

class BookingProvider:
    name = "booking"

    async def _parse(self, page: Page, base_url: str) -> List[Listing]:
        cards = await page.query_selector_all('[data-testid="property-card"]')

        # ✅ cards=0이면 디버그 저장
        if not cards:
            from src.utils.debug_dump import dump_page
            await dump_page(page, "booking_zero")
            return []

        out: List[Listing] = []

        for i, c in enumerate(cards[:25]):
            title_el = await c.query_selector('[data-testid="title"]')
            title = (await title_el.inner_text()).strip() if title_el else f"listing-{i}"

            link_el = await c.query_selector('a[data-testid="title-link"]')
            href = await link_el.get_attribute("href") if link_el else None
            url = urljoin(base_url, href) if href else base_url

            _id = re.sub(r"[^a-zA-Z0-9]+", "_", url)[:120]

            price_el = await c.query_selector('[data-testid="price-and-discounted-price"]')
            price_text = (await price_el.inner_text()) if price_el else ""
            price_total = _to_int_price(price_text)

            rating_el = await c.query_selector('[data-testid="review-score"]')
            rating_text = (await rating_el.inner_text()).strip() if rating_el else ""
            rating = _to_float_rating(rating_text)

            # (참고) reviews 파싱은 booking의 review-score 텍스트 구조가 바뀌어서
            # 지금 로직이 부정확할 수 있음. 일단 유지.
            reviews = None
            if rating_el:
                t = (await rating_el.inner_text())
                m = re.search(r"(\d[\d,]*)", t)
                if m:
                    reviews = int(m.group(1).replace(",", ""))

            loc_el = await c.query_selector('[data-testid="address"]')
            loc = (await loc_el.inner_text()).strip() if loc_el else None

            out.append(Listing(
                provider=self.name,
                id=_id,
                title=title,
                url=url,
                price_total=price_total,
                rating=rating,
                reviews=reviews,
                free_cancel=None,
                location_text=loc,
            ))
        return out

    async def fetch(self, url: str) -> List[Listing]:
        async with browser_context(headless=True) as ctx:
            page = await ctx.new_page()
            await page.set_viewport_size({"width": 1280, "height": 800})
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # ✅ 렌더링/요청 안정화
            try:
                await page.wait_for_load_state("networkidle", timeout=30000)
            except Exception:
                pass

            # 쿠키/팝업 닫기
            for sel in ['button#onetrust-accept-btn-handler', '[data-testid="cookie-banner"] button']:
                btn = await page.query_selector(sel)
                if btn:
                    try:
                        await btn.click(timeout=1000)
                    except Exception:
                        pass

            # ✅ 스크롤로 카드 로드 유도
            for _ in range(3):
                await page.mouse.wheel(0, 2500)
                await page.wait_for_timeout(700)

            # ✅ 카드가 뜰 때까지 기다림 (안 뜨면 덤프)
            try:
                await page.wait_for_selector('[data-testid="property-card"]', timeout=15000)
            except Exception:
                from src.utils.debug_dump import dump_page
                await dump_page(page, "booking_no_cards")
                return []

            return await self._parse(page, base_url=url)
