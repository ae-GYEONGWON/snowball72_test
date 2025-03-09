from pydantic import BaseModel


class BacktestReq(BaseModel):
    start_year: int
    start_month: int
    initial_investment: float
    trade_date: int
    trading_fee: float
    rebalance_period: int

    class Config:
        json_schema_extra = {
            "example": {
                "start_year": 2020,
                "start_month": 1,
                "initial_investment": 1000.0,
                "trade_date": 15,
                "trading_fee": 0.001,
                "rebalance_period": 3,
            }
        }


class BacktestResp(BaseModel):
    data_id: str
    output: dict[str, float]  # total_return, cagr, vol, sharpe, mdd
    last_rebalance_weight: list[tuple[str, float]]  # ETF 비중
