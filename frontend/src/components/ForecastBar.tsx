import type { Forecast } from '../api/types';
import { formatCurrency, formatMonth } from '../lib/format';
import { Icon } from './Icon';
import { ReliabilityPill } from './ReliabilityPill';

export function ForecastBar({ forecast }: { forecast: Forecast }) {
  return (
    <section className="forecast-bar" aria-label="Next month forecast">
      <div className="forecast-bar__main">
        <span className="forecast-bar__label">
          {formatMonth(forecast.target_month, 'long')} forecast
        </span>
        <span className="forecast-bar__value">{formatCurrency(forecast.baseline)}</span>
        <span className="forecast-bar__range">
          {formatCurrency(forecast.optimistic)} to {formatCurrency(forecast.conservative)}
        </span>
        <ReliabilityPill reliability={forecast.reliability} />
      </div>
      <a className="forecast-bar__link" href="#forecast">
        Forecast details
        <Icon name="arrow_forward" size={16} />
      </a>
    </section>
  );
}
