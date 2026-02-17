
from __future__ import annotations
from typing import List, Optional
from playwright.async_api import Page

async def wait_and_pick_selector(page: Page, selectors: List[str], timeout_ms: int = 20000) -> Optional[str]:
    for sel in selectors:
        try:
            await page.wait_for_selector(sel, timeout=timeout_ms)
            return sel
        except Exception:
            continue
    return None

async def scroll_a_bit(page: Page, times: int = 4, dy: int = 2500, pause_ms: int = 700) -> None:
    for _ in range(times):
        await page.mouse.wheel(0, dy)
        await page.wait_for_timeout(pause_ms)
