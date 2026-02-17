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

class TripProvider:
    name = "trip"

    async def _parse(self, page: Page, base_url: str) -> List[Listing]:
        # ✅ 1) 카드가 뜰 때까지 기다릴 후보 셀렉터들
        candidates = [
            "[data-testid='hotel-card']",
            "[data-testid='property-card']",
            "div[property='itemListElement']",
            "a[href*='/hotels/']",
        ]

        found_sel = None
        for sel in candidates:
            try:
                await page.wait_for_selector(sel, timeout=15000)
                found_sel = sel
                break
            except Exception:
                pass

        # ✅ 2) 아무것도 못 찾으면: 차단/캡차 가능성 → 디버그 덤프
        if not found_sel:
            from src.utils.debug_dump import dump_page
            await dump_page(page, "trip_no_selector")

            html = (await page.content()).lower()
            if any(k in html for k in ["captcha", "verify", "access denied", "bot"]):
                # 차단 화면이면 여기서 멈춤
                return []
            return []

        # ✅ 3) 카드 목록 가져오기 (selector가 a면 링크 기준으로 카드처럼 처리)
        nodes = await page.query_selector_all(found_sel)
        if not nodes:
            from src.utils.debug_dump import dump_page
            await dump_page(page, "trip_zero")
            return []

        out: List[Listing] = []

        # 링크 기반 selector면 중복 제거를 위해 href set 사용
        seen = set()

        for i, n in enumerate(nodes[:25]):
            # title
            title_el = await n.query_selector("h2, h3, [data-testid='hotel-name']")
            title = (await title_el.inner_text()).strip() if title_el else f"listing-{i}"

            # link
            link_el = n
            href = await link_el.get_attribute("href")
            if not href:
                a = await n.query_selector("a[href]")
                href = await a.get_attribute("href") if a else None

            if not href:
                continue

            url = urljoin(base_url, href)
            if url in seen:
                continue
            seen.add(url)

            _id = re.sub(r"[^a-zA-Z0-9]+", "_", url)[:120]

            # price (Trip.com DOM은 자주 바뀜 → 후보로 넓게)
            price_el = await n.query_selector("[data-testid='price'], [class*='price'], [class*='Price']")
            price_text = (await price_el.inner_text()) if price_el else ""
            price_total = _to_int_price(price_text)

            # rating
            rating_el = await n.query_selector("[data-testid='rating'], [class*='score'], [class*='Score']")
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

        # ✅ 4) 결과가 0이면 페이지를 덤프해둔다 (selector는 맞는데 파싱이 틀린 경우)
        if not out:
            from src.utils.debug_dump import dump_page
            await dump_page(page, "trip_parsed_zero")

        return out

    async def fetch(self, url: str) -> List[Listing]:
        async with browser_context(headless=True) as ctx:
            page = await ctx.new_page()
            await page.set_viewport_size({"width": 1280, "height": 800})

            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # ✅ 1) 렌더링 안정화
            try:
                await page.wait_for_load_state("networkidle", timeout=30000)
            except Exception:
                pass

            # ✅ 2) 스크롤로 로딩 유도
            for _ in range(3):
                await page.mouse.wheel(0, 2500)
                await page.wait_for_timeout(700)

            # ✅ 3) 파싱
            return await self._parse(page, base_url=url)
