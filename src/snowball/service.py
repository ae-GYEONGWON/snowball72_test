from datetime import date

from sqlalchemy.orm import Session

from src.snowball.models import Stock


# DB에서 데이터 조회
def get_by_date(db: Session, ticker: str, start_date: date, end_date: date):
    return (
        db.query(Stock)
        .filter(
            Stock.ticker == ticker,
            Stock.date >= start_date,
            Stock.date <= end_date,
        )
        .order_by(Stock.date)
        .all()
    )
