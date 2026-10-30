import { ApiError } from '../api/client';
import type { Forecast as ForecastData } from '../api/types';
import { Async } from '../components/Async';
import { BacktestTable } from '../components/BacktestTable';
import { Icon } from '../components/Icon';
import { ReliabilityPill } from '../components/ReliabilityPill';
import { useForecast } from '../hooks/useForecast';
import { formatCurrency, formatMonth } from '../lib/format';

const METHOD_TEXT: Record<ForecastData['method'], string> = {
  empirical_quantile: 'Observed forecast errors',
  t_approximation: 't-distribution estimate',
};

function Tile({
  label,
  value,
  hint,
  emphasis = false,
}: {
  label: string;
  value: number;
  hint: string;
  emphasis?: boolean;
}) {
  return (
    <div className={`card score${emphasis ? ' score--focus' : ''}`}>
      <span className="metric__label">{label}</span>
      <span className="score__value">{formatCurrency(value)}</span>
      <span className="card__sub">{hint}</span>
    </div>
  );
}

function ForecastView({ forecast }: { forecast: ForecastData }) {
  return (
    <>
      <section className="card model-summary">
        <div>
          <ReliabilityPill reliability={forecast.reliability} />
          <h2 className="card__title">{formatMonth(forecast.target_month, 'long')}</h2>
          <p className="card__sub">Expected total spending</p>
        </div>
        <dl className="facts">
          <div>
            <dt>History used</dt>
            <dd>{forecast.history_months} months</dd>
          </div>
          <div>
            <dt>Since</dt>
            <dd>{formatMonth(forecast.history_start, 'long')}</dd>
          </div>
          <div>
            <dt>Range based on</dt>
            <dd>{METHOD_TEXT[forecast.method]}</dd>
          </div>
        </dl>
      </section>

      <section className="score-grid" aria-label="Forecast scenarios">
        <Tile label="Optimistic" value={forecast.optimistic} hint="If spending comes in low" />
        <Tile
          label="Baseline"
          value={forecast.baseline}
          hint="Most likely, from the best model"
          emphasis
        />
        <Tile label="Conservative" value={forecast.conservative} hint="If spending comes in high" />
      </section>

      {forecast.warning && (
        <section className="review-banner review-banner--stack" aria-label="Forecast warning">
          <Icon name="warning" size={20} className="tone-warning" />
          <p>{forecast.warning}</p>
        </section>
      )}

      <BacktestTable
        perModel={forecast.backtest.per_model}
        selected={forecast.selected_model}
        errorsUsed={forecast.backtest.residuals_used}
      />
    </>
  );
}

function NotEnoughData({ message }: { message: string }) {
  return (
    <section className="card empty-model">
      <Icon name="trending_up" size={32} className="tone-muted" />
      <h2 className="card__title">Not enough history yet</h2>
      <p>{message}</p>
    </section>
  );
}

export default function Forecast() {
  const query = useForecast();
  const notEnough = query.error instanceof ApiError && query.error.code === 'INSUFFICIENT_DATA';

  return (
    <div className="dashboard">
      <section className="page-head">
        <div className="dashboard__intro">
          <h1>Forecast</h1>
          <p>
            Next month&apos;s total spending, with a low and a high scenario. It uses completed
            months only, and ignores categories.
          </p>
        </div>
        <button type="button" className="btn" onClick={query.reload}>
          <Icon name="refresh" size={16} /> Recalculate
        </button>
      </section>
      {notEnough ? (
        <NotEnoughData message={query.error?.message ?? ''} />
      ) : (
        <Async query={query} minHeight={320}>
          {(forecast) => <ForecastView forecast={forecast} />}
        </Async>
      )}
    </div>
  );
}
