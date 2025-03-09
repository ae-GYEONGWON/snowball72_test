from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.snowball.flows import load_excel_to_db, run_backtest
from src.snowball.schema import BacktestReq, BacktestResp

router = APIRouter()


@router.post("/history", response_model=None)
def fetch_and_store_etf_prices(db: Session = Depends(get_db)):
    try:
        # SPY, QQQ, GLD, BIL 데이터 가져오기
        load_excel_to_db(db=db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 저장 실패: {str(e)}")


@router.post("/backtest")
def backtest_endpoint(backtest_req: BacktestReq, db: Session = Depends(get_db)):
    """입력을 받아 작성한 계산 로직을 실행, 저장하고, 저장 항목의 key 인 data_id 와 통계값을 반환하는 API"""
    result = run_backtest(db, backtest_req)
    return BacktestResp(**result)


@router.get("/backtest/list")
def get_data_id_list(db: Session = Depends(get_db)):
    """저장된 data_id 목록을 반환하는 API"""
    return


@router.get("/backtest/{data_id}")
def get_detail_by_data_id(db: Session = Depends(get_db)):
    """data_id 에 해당하는 저장 항목을 불러와 계산한 통계값과  마지막 리밸런싱 비중을 반환하는 API"""
    return


@router.delete("/backtest/{data_id}")
def delete_by_data_id(db: Session = Depends(get_db)):
    """data_id 에 해당하는 항목을 삭제하는 API"""
    return
