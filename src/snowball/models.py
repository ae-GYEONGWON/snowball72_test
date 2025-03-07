from datetime import date as dt_date

from sqlalchemy import Date, Numeric, PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class Stock(Base):
    __tablename__ = "stock"

    date: Mapped[dt_date] = mapped_column(Date, nullable=False)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(13, 4), nullable=False)

    __table_args__ = (PrimaryKeyConstraint("date", "ticker"),)

    def __repr__(self):
        return f"<Stock(date={self.date}, ticker={self.ticker}, price={self.price})>"
