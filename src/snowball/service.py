from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.snowball.models import BacktestResult, Stock


def get_by_date(db: Session, ticker: str, start_date: date, end_date: date):
    """Stock 테이블의 특정 데이터 조회"""
    stmt = (
        select(Stock)
        .where(
            Stock.ticker == ticker,
            Stock.date.between(start_date, end_date),
        )
        .order_by(Stock.date)
    )
    return db.execute(stmt).scalars().all()


def get_all_backtest_ids_with_weights(db: Session):
    """BacktestResult 테이블의 모든 데이터를 조회"""
    stmt = select(BacktestResult.data_id, BacktestResult.rebalance_weights)
    return db.execute(stmt).all()


def get_backtest_result_by_id(db: Session, data_id: int):
    """data_id에 해당하는 백테스트 결과 조회"""
    stmt = select(BacktestResult).where(BacktestResult.data_id == data_id)
    result = db.execute(stmt).scalar_one_or_none()
    return result


def delete_backtest_result_by_id(db: Session, data_id: int) -> bool:
    """해당 data_id를 가진 백테스트 결과를 삭제하는 함수"""
    stmt = delete(BacktestResult).where(BacktestResult.data_id == data_id)
    result = db.execute(stmt)
    db.commit()

    # 삭제된 행이 있는 경우 True 반환
    return result.rowcount > 0
