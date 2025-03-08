from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from src.snowball.models import Stock
from src.snowball.schema import BacktestInput
from src.snowball.service import get_by_date


def load_excel_to_db(db: Session):
    """엑셀 파일에서 종가 데이터를 읽어 DB에 저장"""
    # ✅ 엑셀 데이터 불러오기
    EXCEL_FILE_PATH = "src/snowball/백엔드 과제.xlsx"
    df = pd.read_excel(EXCEL_FILE_PATH, sheet_name="가격")
    df = df.iloc[:, :6]
    df = df.set_axis(["Date", "SPY", "QQQ", "GLD", "TIP", "BIL"], axis=1)

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
    df = df.dropna()

    # ✅ 종목별로 저장
    for _, row in df.iterrows():
        for ticker in ["SPY", "QQQ", "GLD", "TIP", "BIL"]:
            stock_data = Stock(date=row["Date"], ticker=ticker, price=row[ticker])
            db.merge(stock_data)  # ✅ 중복 저장 방지 (이미 있으면 업데이트)

    db.commit()
    print("✅ 엑셀 데이터가 성공적으로 DB에 저장되었습니다.")


# ✅ 리밸런싱 날짜 및 비중을 미리 계산
def calculate_rebalance_date_and_weights(
    start_date: datetime,
    end_date: datetime,
    backtest_input: BacktestInput,
    df: pd.DataFrame,
) -> dict[datetime, dict[str, float]]:
    rebalance_info = {}
    current_date = start_date

    while current_date <= end_date:
        # 🔹 trade_date 설정 (없으면 가장 가까운 거래일 선택)
        trade_date = datetime(
            current_date.year, current_date.month, backtest_input.trade_date
        )
        df.index = pd.to_datetime(df.index)
        trade_date = pd.Timestamp(trade_date)
        # valid_dates = df.index[df.index.year == trade_date.year][
        #     df.index.month == trade_date.month  # type: ignore[attr-defined]
        # ]
        valid_dates = df.index[
            (df.index.year == trade_date.year) & (df.index.month == trade_date.month)
        ]

        if trade_date not in valid_dates:
            trade_date = valid_dates[
                valid_dates < trade_date
            ].max()  # 가장 가까운 날짜 찾기

        if pd.notna(trade_date):  # 유효한 날짜만 저장
            # ✅ rebalance_period 전의 데이터만 사용
            rebalance_start_date = trade_date - pd.DateOffset(
                months=backtest_input.rebalance_period
            )
            period_data = df.loc[rebalance_start_date:trade_date]  # type: ignore[misc] # rebalance_start_date를 intager로 예상함.
            rebalance_info[trade_date] = calculate_weights(
                period_data, backtest_input.rebalance_period
            )

        # ✅ rebalance_period 개월 뒤로 이동
        next_month = (current_date.month - 1 + backtest_input.rebalance_period) % 12 + 1
        next_year = (
            current_date.year
            + (current_date.month - 1 + backtest_input.rebalance_period) // 12
        )
        current_date = datetime(next_year, next_month, 1)  # 🔹 정확한 월 이동

    return rebalance_info


# 최근 N개월 수익률 계산
def calculate_momentum(df: pd.DataFrame | pd.Series, period: int):
    return df.pct_change(periods=period).iloc[-1]


# 비중 계산
def calculate_weights(df: pd.DataFrame, rebalance_period: int) -> dict[str, float]:
    TIP = "TIP"
    SAFE_ASSET = "BIL"

    # TIP 절대 모멘텀 계산 (6개월 수익률)
    tip_momentum = calculate_momentum(df[TIP], rebalance_period)

    # 안전자산(BIL) 여부 결정
    if tip_momentum < 0:
        return {SAFE_ASSET: 1.0}  # 안전자산 100% 투자

    # SPY, QQQ, GLD 중 상대 모멘텀 계산
    candidates = ["SPY", "QQQ", "GLD"]
    momentum_scores = calculate_momentum(df[candidates], rebalance_period)
    # 상위 2개 ETF 선택
    momentum_scores = momentum_scores.astype(float)
    top_two = momentum_scores.nlargest(2).index.tolist()

    # 비중 할당 (50%씩)
    weights = {ticker: 0.5 if ticker in top_two else 0 for ticker in candidates}

    return weights


# 백테스트 실행
def run_backtest(db: Session, backtest_input: BacktestInput):
    tickers = ["SPY", "QQQ", "GLD", "TIP", "BIL"]
    # ETF 가격 데이터 가져오기
    start_date = datetime(backtest_input.start_year, backtest_input.start_month, 1)
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
        start_date=start_date, end_date=end_date, backtest_input=backtest_input, df=df
    )
    # 리밸런싱 로직 실행
    cash = backtest_input.initial_investment
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

            trading_fee = backtest_input.trading_fee
            total_buy_cost = 0
            total_sell_cost = 0

            # 포트폴리오 조정
            for ticker, weight in weights.items():
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
            nav_history.append((date, total_nav))

            # print("weights: ", weights)
            # print(
            #     "stock_data: ",
            #     [(ticker, holdings[ticker] * row[ticker]) for ticker in holdings],
            # )
            # print("trading_fee: ", trading_fee)

    # 결과 데이터프레임
    nav_df = pd.DataFrame(nav_history, columns=["date", "nav"])

    return {
        "nav_history": nav_df.to_dict(orient="records"),
        "last_rebalance_weight": weights,
    }
