from sqlalchemy import Column, Date, Numeric, PrimaryKeyConstraint, String

from src.database import Base


class Stock(Base):
    __tablename__ = "stock"

    date = Column(Date, nullable=False)
    ticker = Column(String(10), nullable=False)
    price = Column(Numeric(13, 4), nullable=False)

    __table_args__ = (PrimaryKeyConstraint("date", "ticker"),)
