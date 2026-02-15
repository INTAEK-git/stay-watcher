from __future__ import annotations
from urllib.parse import urlencode

def booking_search_url(city: str, checkin: str, checkout: str, adults: int, children: int, rooms: int) -> str:
    # 가장 단순하고 안정적인 쿼리
    params = {
        "ss": city,
        "checkin": checkin,
        "checkout": checkout,
        "group_adults": adults,
        "group_children": children,
        "no_rooms": rooms,
    }
    return "https://www.booking.com/searchresults.html?" + urlencode(params)

def agoda_search_url(city: str, checkin: str, checkout: str, adults: int, children: int, rooms: int) -> str:
    # Agoda는 지역/언어에 따라 달라져서 “검색 키워드 기반 URL”로 단순화
    # (정확도가 더 필요하면 city->cityId 매핑 테이블을 추가로 두는 방식 추천)
    params = {
        "cityName": city,
        "checkIn": checkin,
        "checkOut": checkout,
        "adults": adults,
        "children": children,
        "rooms": rooms,
        "locale": "ko-kr",
        "currency": "KRW",
    }
    return "https://www.agoda.com/ko-kr/search?" + urlencode(params)
