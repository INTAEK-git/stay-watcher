from __future__ import annotations
import re
from typing import List, Optional
from urllib.parse import urljoin
from playwright.async_api import Page
from src.providers.base import Listing
from urllib.parse import urlparse
from src.utils.playwright_pool import browser_context

def _to_int_price(text: str) -> Optional[int]:
    nums = re.findall(r"\d[\d,]*", text.replace(".", ""))
    if not nums:
        return None
    return int(nums[0].replace(",", ""))

def _to_float_rating(text: str) -> Optional[float]:
    m = re.search(r"(\d+(?:\.\d+)?)", text)
    return float(m.group(1)) if m else None

async def scroll_a_bit(page, max_scrolls=8):
    last_height = await page.evaluate("document.body.scrollHeight")

    for _ in range(max_scrolls):
        await page.mouse.wheel(0, 3000)
        await page.wait_for_timeout(800)

        new_height = await page.evaluate("document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height



AGODA_ORIGIN = "https://www.agoda.com"

class AgodaProvider:
    name = "agoda"

    async def _parse(self, page: Page, base_url: str) -> List[Listing]:
            # ✅ 렌더링 대기 + 스크롤
        try:
            await page.wait_for_load_state("networkidle", timeout=25000)
        except Exception:
            pass
        await scroll_a_bit(page)
        
        
        
        
        # ✅ 카드가 뜰 때까지 기다림 (여러 후보 중 하나라도)
        candidates = [
            'div[data-selenium="hotel-item"]',
            'li[data-selenium="hotel-item"]',
            '[data-element-name="hotel-card"]',
            'div[property="itemListElement"]',
        ]

        found_sel = None
        for sel in candidates:
            try:
                await page.wait_for_selector(sel, timeout=15000)
                found_sel = sel
                break
            except Exception:
                pass

        if not found_sel:
            # 캡차/차단 여부 간단 감지
            html = await page.content()
            if any(k in html.lower() for k in ["captcha", "verify", "access denied", "bot"]):
                raise RuntimeError("Agoda 차단/캡차 페이지로 보입니다 (headless/UA 이슈 가능).")
            return []

        # ✅ 스크롤로 추가 로드 유도 (3~5회 정도)
        for _ in range(4):
            await page.mouse.wheel(0, 2500)
            await page.wait_for_timeout(800)

        cards = await page.query_selector_all(found_sel)
        out: List[Listing] = []

        # base_url은 검색URL 말고 origin 사용 추천
        base = AGODA_ORIGIN

        for i, c in enumerate(cards[:25]):
            title_el = await c.query_selector('[data-selenium="hotel-name"], [data-testid="hotel-name"]')
            title = (await title_el.inner_text()).strip() if title_el else f"listing-{i}"

            link_el = await c.query_selector('a[href*="hotel"], a[href*="accommodation"]')
            href = await link_el.get_attribute("href") if link_el else None
            url = urljoin(base, href) if href else page.url

            _id = re.sub(r"[^a-zA-Z0-9]+", "_", url)[:120]

            price_el = await c.query_selector('[data-selenium="display-price"], [data-selenium="price"], [data-testid="price"]')
            price_text = (await price_el.inner_text()) if price_el else ""
            price_total = _to_int_price(price_text)

            rating_el = await c.query_selector('[data-selenium="hotel-rating"], span[data-selenium="review-score"], [data-testid="review-score"]')
            rating_text = (await rating_el.inner_text()) if rating_el else ""
            rating = _to_float_rating(rating_text)

            out.append(Listing(
                provider=self.name,
                id=_id,
                title=title,
                url=url,
                price_total=price_total,
                rating=rating,
                reviews=None,
                free_cancel=None,
                location_text=None,
            ))
        return out

    async def fetch(self, url: str) -> List[Listing]:
        async with browser_context(headless=True) as ctx:
            page = await ctx.new_page()

            # ✅ 아고다용 세팅(가능하면 browser_context 쪽으로 올리는 게 더 좋음)
            await page.set_viewport_size({"width": 1280, "height": 800})

            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            try:
                await page.wait_for_load_state("networkidle", timeout=30000)
            except Exception:
                pass

            # 쿠키/팝업 닫기
            for sel in ['button#onetrust-accept-btn-handler', 'button[aria-label="Close"]']:
                btn = await page.query_selector(sel)
                if btn:
                    try:
                        await btn.click(timeout=1000)
                    except Exception:
                        pass

            return await self._parse(page, base_url=url)
