import type { ReactNode } from 'react';
import type { MonthlySummary } from '../api/types';
import { formatCurrency, formatPercent, formatSigned } from '../lib/format';
import { computeDelta, savingsRate, type Delta } from '../lib/metrics';
import { Icon } from './Icon';

interface MetricCardProps {
  label: string;
  icon: string;
  iconTone: 'positive' | 'neutral';
  value: string;
  valueTone?: 'positive' | 'negative';
  children: ReactNode;
}

function MetricCard({ label, icon, iconTone, value, valueTone, children }: MetricCardProps) {
  return (
    <div className="card metric">
      <div className="metric__head">
        <span className="metric__label">{label}</span>
        <Icon name={icon} size={18} className={`tone-${iconTone}`} />
      </div>
      <div className={`metric__value${valueTone ? ` metric__value--${valueTone}` : ''}`}>
        {value}
      </div>
      <div className="metric__foot">{children}</div>
    </div>
  );
}

function DeltaPill({ delta, goodWhen }: { delta: Delta | null; goodWhen: 'up' | 'down' }) {
  if (!delta) return <span className="pill pill--neutral">Comparison unavailable</span>;

  const icon = delta.diff > 0 ? 'arrow_upward' : delta.diff < 0 ? 'arrow_downward' : 'remove';
  let tone = 'neutral';
  if (delta.diff !== 0) tone = delta.diff > 0 === (goodWhen === 'up') ? 'positive' : 'warning';
  const pct = delta.pct === null ? '' : ` (${formatPercent(Math.abs(delta.pct))})`;

  return (
    <span className={`pill pill--${tone}`}>
      <Icon name={icon} size={14} />
      {formatSigned(delta.diff)}
      {pct} vs last month
    </span>
  );
}

interface SummaryCardsProps {
  summary: MonthlySummary;
  /** Previous month's summary; null while loading or if it failed to load. */
  previous: MonthlySummary | null;
}

export function SummaryCards({ summary, previous }: SummaryCardsProps) {
  const incomeDelta = previous ? computeDelta(summary.income, previous.income) : null;
  const expenseDelta = previous ? computeDelta(summary.expense, previous.expense) : null;
  const rate = savingsRate(summary.income, summary.net);

  return (
    <section className="metric-grid" aria-label="Monthly summary">
      <MetricCard
        label="Monthly income"
        icon="south_west"
        iconTone="positive"
        value={formatCurrency(summary.income)}
      >
        <DeltaPill delta={incomeDelta} goodWhen="up" />
      </MetricCard>

      <MetricCard
        label="Monthly spending"
        icon="north_east"
        iconTone="neutral"
        value={formatCurrency(summary.expense)}
      >
        <DeltaPill delta={expenseDelta} goodWhen="down" />
      </MetricCard>

      <MetricCard
        label="Net cash flow"
        icon="savings"
        iconTone="positive"
        value={formatSigned(summary.net)}
        valueTone={summary.net < 0 ? 'negative' : 'positive'}
      >
        {rate === null ? (
          <span className="pill pill--neutral">No income recorded</span>
        ) : (
          <span className={`pill pill--${rate >= 0 ? 'positive' : 'warning'}`}>
            <Icon name="insights" size={14} />
            {formatPercent(rate)} savings rate
          </span>
        )}
      </MetricCard>
    </section>
  );
}
