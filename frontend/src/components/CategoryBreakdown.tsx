import { useState } from 'react';
import { Pie, PieChart, ResponsiveContainer } from 'recharts';
import type { MonthlySummary } from '../api/types';
import { formatCurrency, formatCurrencyFit, formatPercent } from '../lib/format';
import { groupTopN } from '../lib/metrics';
import { CATEGORY_COLORS } from '../lib/palette';
import { Icon } from './Icon';

const MAX_SLICES = 5;
/** Longest amount that fits inside the ring before switching to a compact form. */
const DONUT_MAX_CHARS = 12;

export function CategoryBreakdown({ summary }: { summary: MonthlySummary }) {
  const [activeKey, setActiveKey] = useState<string | null>(null);

  const expenses = summary.by_category.filter((c) => c.type === 'expense');
  const slices = groupTopN(expenses, MAX_SLICES).map((slice, index) => ({
    ...slice,
    fill: CATEGORY_COLORS[index % CATEGORY_COLORS.length],
  }));
  const active = slices.find((s) => s.key === activeKey) ?? null;

  return (
    <div className="card chart-card">
      <div className="card__head">
        <div>
          <h2 className="card__title">Spending breakdown</h2>
          <p className="card__sub">By category, this month</p>
        </div>
        <Icon name="pie_chart" className="tone-muted" />
      </div>

      <div className="donut">
        {slices.length === 0 ? (
          <div className="donut__empty" />
        ) : (
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie
                data={slices}
                dataKey="total"
                nameKey="label"
                innerRadius="74%"
                outerRadius="100%"
                paddingAngle={slices.length > 1 ? 2 : 0}
                stroke="none"
                onMouseEnter={(_, index) => setActiveKey(slices.at(index)?.key ?? null)}
                onMouseLeave={() => setActiveKey(null)}
              />
            </PieChart>
          </ResponsiveContainer>
        )}
        <div className="donut__center" aria-hidden="true">
          <span className="donut__label">{active ? active.label : 'Total'}</span>
          <span className="donut__amount">
            {formatCurrencyFit(active ? active.total : summary.expense, DONUT_MAX_CHARS)}
          </span>
        </div>
      </div>

      {slices.length === 0 ? (
        <p className="empty-note">No spending recorded for this month.</p>
      ) : (
        <ul className="chips">
          {slices.map((slice) => (
            <li key={slice.key}>
              <button
                type="button"
                className="chip"
                aria-label={`${slice.label}, ${formatPercent(slice.pct, 0)}, ${formatCurrency(slice.total)}`}
                onMouseEnter={() => setActiveKey(slice.key)}
                onMouseLeave={() => setActiveKey(null)}
                onFocus={() => setActiveKey(slice.key)}
                onBlur={() => setActiveKey(null)}
              >
                <span className="chip__name">
                  <span className="dot" style={{ background: slice.fill }} />
                  <span className="chip__text">{slice.label}</span>
                </span>
                <span className="chip__pct">{formatPercent(slice.pct, 0)}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
