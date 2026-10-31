import { useState } from 'react';
import { Async } from '../components/Async';
import { CategoryBreakdown } from '../components/CategoryBreakdown';
import { ForecastBar } from '../components/ForecastBar';
import { Icon } from '../components/Icon';
import { RecentActivity } from '../components/RecentActivity';
import { ReviewBanner } from '../components/ReviewBanner';
import { SummaryCards } from '../components/SummaryCards';
import { TrendChart } from '../components/TrendChart';
import { useForecast } from '../hooks/useForecast';
import { useMonthlySummary, useTrends } from '../hooks/useSummary';
import { useRecentTransactions, useReviewCount } from '../hooks/useTransactions';
import { formatMonth, greeting, shiftMonth } from '../lib/format';
import type { Horizon } from '../lib/metrics';

/** Shown when the forecast cannot be produced (e.g. not enough history yet). */
function ForecastUnavailable({ error }: { error: Error }) {
  return (
    <section className="forecast-bar forecast-bar--muted" aria-label="Next month forecast">
      <div className="forecast-bar__main">
        <Icon name="trending_up" size={18} className="tone-muted" />
        <span className="forecast-bar__label">Next month forecast</span>
        <span className="forecast-bar__range">{error.message}</span>
      </div>
      <a className="forecast-bar__link" href="#forecast">
        Forecast details
        <Icon name="arrow_forward" size={16} />
      </a>
    </section>
  );
}

export default function Dashboard({ month }: { month: string }) {
  const [horizon, setHorizon] = useState<Horizon>(6);

  const summary = useMonthlySummary(month);
  const previous = useMonthlySummary(shiftMonth(month, -1));
  const trends = useTrends(horizon);
  const recent = useRecentTransactions(5);
  const review = useReviewCount();
  const forecast = useForecast();

  return (
    <div className="dashboard">
      <section className="dashboard__intro">
        <h1>{greeting()}</h1>
        <p>Here is your financial snapshot for {formatMonth(month, 'long')}.</p>
      </section>

      {review.data !== null && review.data > 0 && <ReviewBanner count={review.data} />}

      <Async query={summary} minHeight={140}>
        {(data) => (
          <SummaryCards summary={data} previous={previous.loading ? null : previous.data} />
        )}
      </Async>

      {forecast.data !== null ? (
        <ForecastBar forecast={forecast.data} />
      ) : (
        forecast.error && <ForecastUnavailable error={forecast.error} />
      )}

      <div className="dashboard__charts">
        <Async query={trends} minHeight={380}>
          {(points) => (
            <TrendChart
              points={points}
              selectedMonth={month}
              horizon={horizon}
              onHorizonChange={setHorizon}
            />
          )}
        </Async>
        <Async query={summary} minHeight={380}>
          {(data) => <CategoryBreakdown summary={data} />}
        </Async>
      </div>

      <Async query={recent} minHeight={200}>
        {(page) => <RecentActivity page={page} />}
      </Async>
    </div>
  );
}
