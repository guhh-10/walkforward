import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.forecast import ForecastOut
from app.services import forecast_service

router = APIRouter(prefix="/api/forecasts", tags=["forecasts"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=ForecastOut)
def create_forecast(db: DbSession) -> ForecastOut:
    """Generate next month's expenditure forecast on demand (nothing is stored)."""
    return forecast_service.generate_forecast(db, dt.date.today())
