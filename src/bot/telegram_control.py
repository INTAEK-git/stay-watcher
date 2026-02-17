from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from .state_store import StateStore
from .query_builders import booking_search_url, agoda_search_url,trip_search_url

from src.app.rules import Rules, match_rules
from src.app.formatter import format_msg

from src.providers.booking import BookingProvider
from src.providers.agoda import AgodaProvider
from src.providers.trip import TripProvider



# ✅ 어디서 실행하든 "프로젝트 루트(.env)"를 확실하게 로드
# 이 파일 위치: stay-watcher/src/bot/telegram_control.py
ROOT_DIR = Path(__file__).resolve().parents[2]  # stay-watcher/
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)


store = StateStore(str(ROOT_DIR / "data" / "search_state.json"))


def _state_text(s) -> str:
    return (
        "📌 현재 조건\n"
        f"- city: {s.city}\n"
        f"- dates: {s.checkin} ~ {s.checkout}\n"
        f"- adults/children/rooms: {s.adults}/{s.children}/{s.rooms}\n"
        f"- min_price: {s.min_total_price}\n"
        f"- max_price: {s.max_total_price}\n"
        f"- min_rating: {s.min_rating}\n"
        f"- free_cancel: {s.require_free_cancel}\n"
        f"- last_run: {s.last_run or '-'}"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = store.load()
    await update.message.reply_text(
        "안녕하세요! 숙소 감시봇 컨트롤입니다.\n\n"
        "명령어:\n"
        "/status\n"
        "/set city 속초\n"
        "/set dates 2026-03-10 2026-03-12\n"
        "/set adults 2\n"
        "/set children 1\n"
        "/set rooms 1\n"
        "/set minprice 150000\n"
        "/set maxprice 300000\n"
        "/set rating 8.0\n"
        "/set freecancel on|off\n"
        "/run booking\n"
        "/run agoda\n"
    )
    await update.message.reply_text(_state_text(s))


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = store.load()
    await update.message.reply_text(_state_text(s))


async def set_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /set key value...
    """
    s = store.load()
    if len(context.args) < 2:
        await update.message.reply_text("사용법: /set <key> <value>\n예: /set city 속초")
        return

    key = context.args[0].lower()
    vals = context.args[1:]

    try:
        if key == "city":
            s.city = " ".join(vals)
        elif key == "dates":
            s.checkin, s.checkout = vals[0], vals[1]
        elif key == "adults":
            s.adults = int(vals[0])
        elif key == "children":
            s.children = int(vals[0])
        elif key == "rooms":
            s.rooms = int(vals[0])
        elif key == "minprice":
            s.min_total_price = int(vals[0])
        elif key == "maxprice":
            s.max_total_price = int(vals[0])
        elif key == "rating":
            s.min_rating = float(vals[0])
        elif key == "freecancel":
            v = vals[0].lower()
            s.require_free_cancel = (v in ("on", "true", "1", "yes", "y"))
        else:
            await update.message.reply_text("지원 key: city/dates/adults/children/rooms/price/rating/freecancel")
            return
    except Exception:
        await update.message.reply_text("값 형식이 올바르지 않습니다. 예: /set rating 8.0")
        return

    store.save(s)
    await update.message.reply_text("✅ 조건이 저장되었습니다.\n" + _state_text(s))


async def run_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /run booking | /run agoda | /run trip
    """
    s = store.load()
    target = (context.args[0].lower() if context.args else "booking")

    rules = Rules(
        min_total_price=s.min_total_price,
        max_total_price=s.max_total_price,
        min_rating=s.min_rating,
        require_free_cancel=s.require_free_cancel,
    )

    if target == "booking":
        url = booking_search_url(
                                    s.city,
                                    s.checkin,
                                    s.checkout,
                                    s.adults,
                                    s.children,
                                    s.rooms,
                                )
        provider = BookingProvider()
    elif target == "agoda":
        url = agoda_search_url(
                                    s.city,
                                    s.checkin,
                                    s.checkout,
                                    s.adults,
                                    s.children,
                                    s.rooms,
                                )
        provider = AgodaProvider()
    elif target == "trip":
        url = trip_search_url(
                                        s.city, 
                                        s.checkin, 
                                        s.checkout, 
                                        s.adults, 
                                        s.children, 
                                        s.rooms
                                    )
        provider = TripProvider()
    else:
        await update.message.reply_text("사용법: /run booking 또는 /run agoda")
        return

    await update.message.reply_text(f"🔎 실행 시작: {target}\n{url}")

    listings = await provider.fetch(url)

    await update.message.reply_text(
    f"📦 파싱 결과: listings={len(listings)} (target={target})"
)

    matched = [x for x in listings if match_rules(x, rules)]

    await update.message.reply_text(
    f"✅ 조건 통과: matched={len(matched)}"
)

    if not matched:
        await update.message.reply_text("조건에 맞는 숙소가 아직 없어요. (또는 파싱이 안 됐을 수 있어요)")
    else:
        for x in matched[:5]:
            await update.message.reply_text(format_msg(x))

    s.last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    store.save(s)


def main() -> None:
    token = os.getenv("TG_TOKEN")
    if not token:
        raise RuntimeError(
            f"TG_TOKEN이 없습니다. {ENV_PATH} 파일을 확인하세요.\n"
            "예시:\nTG_TOKEN=봇토큰\nTG_CHAT_ID=채팅아이디"
        )

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("set", set_cmd))
    app.add_handler(CommandHandler("run", run_cmd))

    # Polling 시작
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
