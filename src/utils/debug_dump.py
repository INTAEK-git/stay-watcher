from __future__ import annotations
from pathlib import Path
from datetime import datetime
from playwright.async_api import Page

async def dump_page(page: Page, tag: str) -> None:
    root = Path(__file__).resolve().parents[2]  # stay-watcher/
    d = root / "data" / "debug"
    d.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    await page.screenshot(path=str(d / f"{tag}_{ts}.png"), full_page=True)
    html = await page.content()
    (d / f"{tag}_{ts}.html").write_text(html, encoding="utf-8")
