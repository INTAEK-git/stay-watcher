from __future__ import annotations

import yaml
from dotenv import load_dotenv
from typing import Dict, Any, List

from utils.logging import log
from storage.seen_store import SeenStore
from notify.telegram import TelegramNotifier
from app.rules import Rules, match_rules
from app.formatter import format_msg

from providers.booking import BookingProvider
from providers.agoda import AgodaProvider
from providers.base import Listing


def load_settings(path: str = "config/settings.yaml") -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


async def run_once() -> None:
    load_dotenv()
    settings = load_settings()

    rules_cfg = settings.get("rules", {})
    rules = Rules(
        min_total_price=int(rules_cfg.get("min_total_price", 0)),
        max_total_price=int(rules_cfg.get("max_total_price", 999999999)),
        min_rating=float(rules_cfg.get("min_rating", 0.0)),
        require_free_cancel=bool(rules_cfg.get("require_free_cancel", False)),
    )


    notifier = TelegramNotifier() if settings.get("telegram", {}).get("enabled", True) else None

    providers = []
    if settings.get("booking", {}).get("enabled", True):
        providers.append(BookingProvider())
    if settings.get("agoda", {}).get("enabled", True):
        providers.append(AgodaProvider())

    total_sent = 0

    for p in providers:
        queries = settings.get(p.name, {}).get("queries", [])
        store = SeenStore(f"data/seen_{p.name}.json")
        seen = store.load()

        log(f"[{p.name}] queries={len(queries)} seen={len(seen)}")

        for q in queries:
            url = q["url"]
            name = q.get("name", "query")
            log(f"[{p.name}] fetch start: {name}")

            listings: List[Listing] = await p.fetch(url)
            log(f"[{p.name}] fetched={len(listings)}")

            for x in listings:
                if x.id in seen:
                    continue
                if not match_rules(x, rules):
                    continue

                if notifier:
                    notifier.send(format_msg(x))

                seen.add(x.id)
                total_sent += 1
                log(f"[{p.name}] sent: {x.title}")

        store.save(seen)

    log(f"done total_sent={total_sent}")
