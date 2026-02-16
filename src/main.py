import asyncio
from app.runner import run_once

if __name__ == "__main__":
    asyncio.run(run_once())

# 실행을 위해서는 다음과 같이 해야함
# python -m src.bot.telegram_control
# 취소는 ctrl + c 