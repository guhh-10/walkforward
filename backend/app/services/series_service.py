import datetime as dt

from sqlalchemy.orm import Session

from app.ml.forecasting import MonthlySeries, build_monthly_series
from app.ml.months import last_complete_month
from app.repositories import series_repository


def expense_series(db: Session, today: dt.date) -> MonthlySeries:
    """Monthly expense totals from the logging anchor to the last complete month.

    Today's month is still in progress, so it is left out; an empty series means
    there is no complete month of history yet.
    """
    anchor = series_repository.first_transaction_date(db)
    if anchor is None:
        return MonthlySeries(months=(), values=())
    return build_monthly_series(
        series_repository.expense_totals_by_month(db),
        anchor,
        last_complete_month(today),
    )
