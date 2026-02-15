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

class AgodaProvider:
    name = "agoda"

    async def _parse(self, page: Page, base_url: str) -> List[Listing]:
        await page.wait_for_timeout(2000)
        cards = await page.query_selector_all('div[data-selenium="hotel-item"], li[data-selenium="hotel-item"]')
        out: List[Listing] = []

        for i, c in enumerate(cards[:25]):
            title_el = await c.query_selector('[data-selenium="hotel-name"]')
            title = (await title_el.inner_text()).strip() if title_el else f"listing-{i}"

            link_el = await c.query_selector('a[href*="hotel"]')
            href = await link_el.get_attribute("href") if link_el else None
            url = urljoin(base_url, href) if href else base_url

            _id = re.sub(r"[^a-zA-Z0-9]+", "_", url)[:120]

            price_el = await c.query_selector('[data-selenium="display-price"], [data-selenium="price"]')
            price_text = (await price_el.inner_text()) if price_el else ""
            price_total = _to_int_price(price_text)

            rating_el = await c.query_selector('[data-selenium="hotel-rating"], span[data-selenium="review-score"]')
            rating_text = (await rating_el.inner_text()) if rating_el else ""
            rating = _to_float_rating(rating_text)

            reviews = None
            reviews_el = await c.query_selector('[data-selenium="review-count"]')
            if reviews_el:
                t = await reviews_el.inner_text()
                m = re.search(r"(\d[\d,]*)", t)
                if m:
                    reviews = int(m.group(1).replace(",", ""))

            loc = None
            loc_el = await c.query_selector('[data-selenium="area-name"]')
            if loc_el:
                loc = (await loc_el.inner_text()).strip()

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
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            for sel in ['button#onetrust-accept-btn-handler', 'button[aria-label="Close"]']:
                btn = await page.query_selector(sel)
                if btn:
                    try:
                        await btn.click(timeout=1000)
                    except Exception:
                        pass

            return await self._parse(page, base_url=url)
