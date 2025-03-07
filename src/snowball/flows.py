import pandas as pd
from sqlalchemy.orm import Session

from src.snowball.models import Stock

EXCEL_FILE_PATH = "src/snowball/백엔드 과제.xlsx"

# 엑셀 데이터 불러오기
df = pd.read_excel(EXCEL_FILE_PATH, sheet_name="예제")


def load_excel_to_db(db: Session):
    """엑셀 파일에서 종가 데이터를 읽어 DB에 저장"""
    # ✅ 엑셀 데이터 불러오기
    df = pd.read_excel(EXCEL_FILE_PATH, sheet_name="예제", header=1)
    df = df.iloc[:, :5]
    df = df.set_axis(["Date", "SPY", "QQQ", "GLD", "BIL"], axis=1)

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
    df = df.dropna()

    # ✅ 종목별로 저장
    for _, row in df.iterrows():
        for ticker in ["SPY", "QQQ", "GLD", "BIL"]:
            stock_data = Stock(date=row["Date"], ticker=ticker, price=row[ticker])
            db.merge(stock_data)  # ✅ 중복 저장 방지 (이미 있으면 업데이트)

    db.commit()
    print("✅ 엑셀 데이터가 성공적으로 DB에 저장되었습니다.")
