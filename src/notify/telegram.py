from __future__ import annotations
import os
import requests


class TelegramNotifier:
    def __init__(self):
        # 환경변수에서 텔레그램 봇 토큰과 채팅 ID를 읽어온다
        self.token = os.getenv("TG_TOKEN")
        self.chat_id = os.getenv("TG_CHAT_ID")

        # 둘 중 하나라도 없으면 실행 중단
        if not self.token or not self.chat_id:
            raise RuntimeError(
                "TG_TOKEN 또는 TG_CHAT_ID가 설정되지 않았습니다.\n"
                "프로젝트 루트의 .env 파일을 확인하세요.\n\n"
                "예시:\n"
                "TG_TOKEN=봇토큰값\n"
                "TG_CHAT_ID=채팅아이디"
            )

    def send(self, text: str) -> None:
        # 텔레그램 메시지 전송 API 주소 생성
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"

        # POST 요청으로 메시지 전송
        response = requests.post(
            url,
            json={
                "chat_id": self.chat_id,
                "text": text,
                "disable_web_page_preview": False,  # 링크 미리보기 허용
            },
            timeout=15,
        )

        # 응답 코드가 200이 아니면 오류 발생
        if response.status_code != 200:
            raise RuntimeError(
                f"텔레그램 전송 실패: {response.status_code}\n"
                f"응답 내용: {response.text}"
            )
