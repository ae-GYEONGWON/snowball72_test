import random
import time
from datetime import UTC, date, datetime
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup

from src.database import SessionLocal
from src.snowball.models import Stock

# ✅ 크롤링 대상 종목
TICKERS = ["SPY", "QQQ", "GLD", "BIL"]

# ✅ User-Agent 설정
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36"
}


# ✅ HTML 요청 함수
def fetch_html(url: str) -> Optional[BeautifulSoup]:
    """야후 파이낸스에서 HTML 데이터를 가져와 BeautifulSoup 객체로 반환"""
    try:
        time.sleep(random.uniform(1, 3))  # 랜덤 딜레이 (429 방지)
        response = requests.get(url, headers=HEADERS)

        if response.status_code == 200:
            return BeautifulSoup(response.text, "html.parser")
        else:
            print(f"⚠️ 요청 실패: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"❌ 요청 중 오류 발생: {e}")
        return None


# ✅ HTML에서 최신 종가 데이터 파싱 함수
def parse_latest_stock_data(soup: BeautifulSoup) -> Optional[Tuple[date, float]]:
    """HTML에서 최신 날짜 및 Adjusted Close 값을 추출"""
    table_rows = soup.select("table tbody tr")

    if table_rows:
        latest_row = table_rows[0].find_all("td")

        if len(latest_row) >= 6:
            latest_date = latest_row[0].text.strip()
            adj_close = latest_row[5].text.strip()

            try:
                latest_date = datetime.strptime(latest_date, "%b %d, %Y").date()
                adj_close = float(adj_close.replace(",", ""))

                return latest_date, adj_close
            except ValueError as e:
                print(f"❌ 데이터 변환 실패: {e}")
                return None
    return None


# ✅ 배치 실행 함수
def run_batch():
    print(f"📌 ETF 가격 업데이트 시작: {datetime.now(UTC)}")

    db = SessionLocal()

    try:
        for ticker in TICKERS:
            url = f"https://finance.yahoo.com/quote/{ticker}/history"
            soup = fetch_html(url)

            if not soup:
                print(f"❌ {ticker} 데이터 가져오기 실패, 스킵")
                break

            stock_data = parse_latest_stock_data(soup)

            if not stock_data:
                print(f"❌ {ticker} Adjusted Close 값 파싱 실패, 스킵")
                break

            latest_date, adj_close = stock_data
            stock_entry = Stock(date=latest_date, ticker=ticker, price=adj_close)
            db.merge(stock_entry)
            print(f"✅ {ticker} 저장 완료: {latest_date} - ${adj_close}")

        db.commit()
        print("✅ 모든 종목 업데이트 완료.")

    except Exception as e:
        db.rollback()
        print(f"❌ 데이터 저장 중 오류 발생: {e}")

    finally:
        db.close()


if __name__ == "__main__":
    run_batch()
