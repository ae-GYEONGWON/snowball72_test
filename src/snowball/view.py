from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.snowball.flows import load_excel_to_db

router = APIRouter()


@router.post("/history", response_model=None)
def fetch_and_store_etf_prices(db: Session = Depends(get_db)):
    try:
        # SPY, QQQ, GLD, BIL 데이터 가져오기
        load_excel_to_db(db=db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 저장 실패: {str(e)}")
