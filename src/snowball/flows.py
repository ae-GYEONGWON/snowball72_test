from datetime import datetime
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from src.snowball.models import BacktestResult, Stock
from src.snowball.schema import BacktestReq
from src.snowball.service import get_by_date


def load_excel_to_db(db: Session):
    """엑셀 파일에서 종가 데이터를 읽어 DB에 저장"""
    EXCEL_FILE_PATH = "src/snowball/백엔드 과제.xlsx"
    df = pd.read_excel(EXCEL_FILE_PATH, sheet_name="가격")
    df = df.iloc[:, :6]
    df = df.set_axis(["Date", "SPY", "QQQ", "GLD", "TIP", "BIL"], axis=1)

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
    df = df.dropna()

    for _, row in df.iterrows():
        for ticker in ["SPY", "QQQ", "GLD", "TIP", "BIL"]:
            stock_data = Stock(date=row["Date"], ticker=ticker, price=row[ticker])
            db.merge(stock_data)

    db.commit()
    print("✅ 엑셀 데이터가 성공적으로 DB에 저장되었습니다.")


# 최근 N개월 수익률 계산
def calculate_momentum(df: pd.DataFrame | pd.Series, period: int):
    return df.pct_change(periods=period).iloc[-1]


# 비중 계산
def calculate_weights(df: pd.DataFrame, rebalance_period: int) -> list[tuple]:
    TIP = "TIP"
    SAFE_ASSET = "BIL"

    # TIP 절대 모멘텀 계산 (6개월 수익률)
    tip_momentum = calculate_momentum(df[TIP], rebalance_period)

    # 안전자산(BIL) 여부 결정
    if tip_momentum < 0:
        return [
            ("SPY", 0),
            ("QQQ", 0),
            ("GLD", 0),
            (SAFE_ASSET, 1.0),
        ]  # 안전자산 100% 투자

    # SPY, QQQ, GLD 중 상대 모멘텀 계산
    candidates = ["SPY", "QQQ", "GLD"]
    momentum_scores = calculate_momentum(df[candidates], rebalance_period)
    # 상위 2개 ETF 선택
    momentum_scores = momentum_scores.astype(float)
    top_two = momentum_scores.nlargest(2).index.tolist()

    # 비중 할당 (50%씩)
    weights = [
        (ticker, 0.5) if ticker in top_two else (ticker, 0) for ticker in candidates
    ]
    weights.append((SAFE_ASSET, 0))

    return weights


# 리밸런싱 날짜 및 비중을 미리 계산
def calculate_rebalance_date_and_weights(
    start_date: datetime,
    end_date: datetime,
    backtest_req: BacktestReq,
    df: pd.DataFrame,
) -> dict[datetime, list[tuple]]:
    rebalance_info = {}
    current_date = start_date

    while current_date <= end_date:
        trade_date = datetime(
            current_date.year, current_date.month, backtest_req.trade_date
        )
        trade_date = pd.Timestamp(trade_date)
        df.index = pd.to_datetime(df.index)
        valid_dates = df.index[
            (df.index.year == trade_date.year) & (df.index.month == trade_date.month)
        ]

        if trade_date not in valid_dates:
            trade_date = valid_dates[valid_dates < trade_date].max()

        if pd.notna(trade_date):  # 유효한 날짜만 저장
            # ✅ rebalance_period 전의 데이터만 사용
            rebalance_start_date = trade_date - pd.DateOffset(
                months=backtest_req.rebalance_period
            )
            period_data = df.loc[rebalance_start_date:trade_date]  # type: ignore[misc] # rebalance_start_date를 intager로 예상함.
            rebalance_info[trade_date] = calculate_weights(
                period_data, backtest_req.rebalance_period
            )

        # ✅ rebalance_period 개월 뒤로 이동
        next_month = (current_date.month - 1 + backtest_req.rebalance_period) % 12 + 1
        next_year = (
            current_date.year
            + (current_date.month - 1 + backtest_req.rebalance_period) // 12
        )
        current_date = datetime(next_year, next_month, 1)  # 🔹 정확한 월 이동

    return rebalance_info


def make_rebalance_weights(rebalance_info) -> list[dict]:
    """rebalance_info를 디비에 저장하기 위한 형식으로 변환"""
    res = []
    for date, weight_data in rebalance_info.items():
        row = {ticker: weight for ticker, weight in weight_data}
        row["date"] = date
        res.append(row)
    return res


def save_backtest_result(
    backtest_req: BacktestReq,
    nav_history: list[dict[str, Any]],
    rebalance_weights: list[dict],
    db: Session,
) -> str:
    data_id = str(uuid4())

    formatted_nav = [
        {**record, "date": record["date"].isoformat()} for record in nav_history
    ]
    formatted_weights = [
        {**record, "date": record["date"].isoformat()} for record in rebalance_weights
    ]

    backtest_result = BacktestResult(
        data_id=data_id,
        start_year=backtest_req.start_year,
        start_month=backtest_req.start_month,
        initial_investment=backtest_req.initial_investment,
        trade_date=backtest_req.trade_date,
        trading_fee=backtest_req.trading_fee,
        rebalance_period=backtest_req.rebalance_period,
        nav_history=formatted_nav,
        rebalance_weights=formatted_weights,
    )
    db.add(backtest_result)
    db.commit()
    return data_id


# 백테스트 실행
def run_backtest(db: Session, backtest_req: BacktestReq) -> dict[str, Any]:
    tickers = ["SPY", "QQQ", "GLD", "TIP", "BIL"]
    # ETF 가격 데이터 가져오기
    start_date = datetime(backtest_req.start_year, backtest_req.start_month, 1)
    end_date = datetime.now()

    price_data = {
        ticker: get_by_date(db, ticker, start_date, end_date) for ticker in tickers
    }

    # 데이터프레임 변환
    df = pd.DataFrame(
        {
            ticker: [entry.price for entry in data]
            for ticker, data in price_data.items()
        },
        index=[entry.date for entry in price_data[tickers[0]]],
    )

    rebalance_info = calculate_rebalance_date_and_weights(
        start_date=start_date, end_date=end_date, backtest_req=backtest_req, df=df
    )
    # 리밸런싱 로직 실행
    cash = backtest_req.initial_investment
    holdings = {ticker: 0 for ticker in tickers}
    nav_history = []

    for date, row in df.iterrows():
        if date in rebalance_info:  # type: ignore[attr-defined]  # Mypy가 date를 Hashable로 오해함
            weights = rebalance_info[date]  # type: ignore[index]  # Mypy가 date를 Hashable로 오해함
            previous_holdings = holdings.copy()
            # 포트폴리오 가치 계산
            total_value = cash + sum(
                holdings[ticker] * row[ticker] for ticker in holdings
            )

            trading_fee = backtest_req.trading_fee
            total_buy_cost = 0
            total_sell_cost = 0

            # 포트폴리오 조정
            for ticker, weight in weights:
                new_shares = (total_value * weight) / row[ticker]
                traded_shares = abs(
                    new_shares - previous_holdings[ticker]
                )  # ✅ 매매된 주식 수
                trade_value = traded_shares * row[ticker]  # ✅ 매매된 금액

                if new_shares > previous_holdings[ticker]:  # ✅ 매수
                    total_buy_cost += trade_value * trading_fee
                elif new_shares < previous_holdings[ticker]:  # ✅ 매도
                    total_sell_cost += trade_value * trading_fee

                holdings[ticker] = new_shares  # ✅ 보유량 업데이트

            cash = (
                total_value
                - sum(holdings[ticker] * row[ticker] for ticker in holdings)
                - total_buy_cost
                - total_sell_cost
            )

            # NAV 기록
            total_nav = cash + sum(
                holdings[ticker] * row[ticker] for ticker in holdings
            )
            nav_history.append({"date": date, "nav": total_nav})

    # 결과 데이터프레임
    rebalance_weights = make_rebalance_weights(rebalance_info)
    data_id = save_backtest_result(backtest_req, nav_history, rebalance_weights, db)
    performance = calculate_performance(nav_history)
    return {
        "data_id": data_id,
        "last_rebalance_weight": weights,
        "output": performance,
    }


def calculate_performance(
    nav_history: list[dict[str, Any]], risk_free_rate: float = 0.02
) -> dict[str, Any]:
    """백테스트 결과에서 통계값 계산"""
    df = pd.DataFrame(nav_history, columns=["date", "nav"])
    df["returns"] = df["nav"].pct_change()

    total_return = df["nav"].iloc[-1] / df["nav"].iloc[0] - 1
    num_years = (df["date"].iloc[-1] - df["date"].iloc[0]).days / 365.25
    cagr = (df["nav"].iloc[-1] / df["nav"].iloc[0]) ** (1 / num_years) - 1
    volatility = df["returns"].std() * np.sqrt(252)
    sharpe_ratio = (cagr - risk_free_rate) / volatility if volatility != 0 else np.nan
    df["cum_max"] = df["nav"].cummax()
    df["drawdown"] = df["nav"] / df["cum_max"] - 1
    mdd = df["drawdown"].min()

    return {
        "total_return": total_return,
        "cagr": cagr,
        "vol": volatility,
        "sharpe": sharpe_ratio,
        "mdd": mdd,
    }
