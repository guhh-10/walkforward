import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.summary import MonthlySummary, TrendPoint
from app.services import summary_service

router = APIRouter(prefix="/api/summary", tags=["summary"])

DbSession = Annotated[Session, Depends(get_db)]

MONTH_PATTERN = r"^(19|20)\d{2}-(0[1-9]|1[0-2])$"


@router.get("/monthly", response_model=MonthlySummary)
def monthly_summary(
    db: DbSession,
    month: Annotated[str | None, Query(pattern=MONTH_PATTERN)] = None,
) -> MonthlySummary:
    """Income, expense, net, and per-category split; defaults to the current month."""
    if month is None:
        month = dt.date.today().strftime("%Y-%m")
    return summary_service.monthly_summary(db, month)


@router.get("/trends", response_model=list[TrendPoint])
def trends(
    db: DbSession,
    months: Annotated[int, Query(ge=1, le=60)] = 12,
) -> list[TrendPoint]:
    """The last N calendar months (oldest first), zero-filled."""
    return summary_service.trends(db, months, dt.date.today())
