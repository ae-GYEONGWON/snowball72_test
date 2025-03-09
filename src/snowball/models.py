from datetime import date as dt_date
from typing import Any

from sqlalchemy import JSON, Date, Float, Integer, PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class Stock(Base):
    __tablename__ = "stock"

    date: Mapped[dt_date] = mapped_column(Date, nullable=False)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (PrimaryKeyConstraint("date", "ticker"),)

    def __repr__(self):
        return f"<Stock(date={self.date}, ticker={self.ticker}, price={self.price})>"


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    data_id: Mapped[str] = mapped_column(
        String, primary_key=True, index=True
    )  # 백테스트 고유 ID
    start_year: Mapped[int] = mapped_column(Integer, nullable=False)
    start_month: Mapped[int] = mapped_column(Integer, nullable=False)
    initial_investment: Mapped[float] = mapped_column(Float, nullable=False)
    trade_date: Mapped[int] = mapped_column(Integer, nullable=False)
    trading_fee: Mapped[float] = mapped_column(Float, nullable=False)
    rebalance_period: Mapped[int] = mapped_column(Integer, nullable=False)

    nav_history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    rebalance_weights: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False
    )
