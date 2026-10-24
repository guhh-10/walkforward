import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { TrendPoint } from '../api/types';
import { currentMonth, formatCompact, formatCurrency, formatMonth } from '../lib/format';
import { HORIZONS, toChartRows, type ChartRow, type Horizon } from '../lib/metrics';
import { COLORS } from '../lib/palette';

interface ChartTooltipProps {
  active?: boolean;
  payload?: readonly { payload?: ChartRow }[];
}

function ChartTooltip({ active, payload }: ChartTooltipProps) {
  const row = payload?.[0]?.payload;
  if (!active || !row) return null;

  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip__title">
        {formatMonth(row.month, 'long')}
        {row.partial && <span className="pill pill--neutral">In progress</span>}
      </div>
      <div className="chart-tooltip__row">
        <span className="legend__swatch" style={{ background: COLORS.income }} />
        <span>Income</span>
        <strong>{formatCurrency(row.income)}</strong>
      </div>
      <div className="chart-tooltip__row">
        <span className="legend__swatch" style={{ background: COLORS.spending }} />
        <span>Spending</span>
        <strong>{formatCurrency(row.expense)}</strong>
      </div>
    </div>
  );
}

interface TrendChartProps {
  points: TrendPoint[];
  selectedMonth: string;
  horizon: Horizon;
  onHorizonChange: (horizon: Horizon) => void;
}

export function TrendChart({ points, selectedMonth, horizon, onHorizonChange }: TrendChartProps) {
  const rows = toChartRows(points, currentMonth());
  const partialRow = rows.find((r) => r.partial) ?? null;
  const isEmpty = points.every((p) => p.income === 0 && p.expense === 0);
  const selectedInRange = points.some((p) => p.month === selectedMonth);

  return (
    <div className="card chart-card">
      <div className="card__head">
        <div>
          <h2 className="card__title">Cash flow trend</h2>
          <p className="card__sub">Monthly income vs spending, last {horizon} months</p>
        </div>
        <div className="segmented" role="group" aria-label="Time range">
          {HORIZONS.map((h) => (
            <button
              key={h}
              type="button"
              className={`segmented__btn${h === horizon ? ' segmented__btn--on' : ''}`}
              aria-pressed={h === horizon}
              onClick={() => onHorizonChange(h)}
            >
              {h} months
            </button>
          ))}
        </div>
      </div>

      <div
        className="chart-box"
        role="img"
        aria-label={`Income and spending for each of the last ${horizon} months`}
      >
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="incomeFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={COLORS.income} stopOpacity={0.18} />
                <stop offset="100%" stopColor={COLORS.income} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke={COLORS.grid} strokeDasharray="4 4" vertical={false} />
            <XAxis
              dataKey="month"
              tickFormatter={(value: string) => formatMonth(value, 'short')}
              tick={{ fontSize: 12, fill: COLORS.axis }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tickFormatter={(value: number) => formatCompact(value)}
              tick={{ fontSize: 12, fill: COLORS.axis }}
              tickLine={false}
              axisLine={false}
              width={52}
            />
            <Tooltip content={<ChartTooltip />} />
            {selectedInRange && (
              <ReferenceLine x={selectedMonth} stroke={COLORS.marker} strokeDasharray="3 3" />
            )}
            <Area
              type="monotone"
              dataKey="incomeSolid"
              stroke={COLORS.income}
              strokeWidth={2.5}
              fill="url(#incomeFill)"
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="incomeDash"
              stroke={COLORS.income}
              strokeWidth={2.5}
              strokeDasharray="6 4"
              fill="none"
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="expenseSolid"
              stroke={COLORS.spending}
              strokeWidth={2.5}
              fill="none"
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="expenseDash"
              stroke={COLORS.spending}
              strokeWidth={2.5}
              strokeDasharray="6 4"
              fill="none"
              isAnimationActive={false}
            />
            {partialRow && (
              <>
                <ReferenceDot
                  x={partialRow.month}
                  y={partialRow.income}
                  r={5}
                  fill="#ffffff"
                  stroke={COLORS.income}
                  strokeWidth={2.5}
                />
                <ReferenceDot
                  x={partialRow.month}
                  y={partialRow.expense}
                  r={5}
                  fill="#ffffff"
                  stroke={COLORS.spending}
                  strokeWidth={2.5}
                />
              </>
            )}
          </AreaChart>
        </ResponsiveContainer>
        {isEmpty && <p className="chart-box__empty">No transactions in this period yet.</p>}
      </div>

      <div className="legend">
        <span className="legend__item">
          <span className="legend__swatch" style={{ background: COLORS.income }} />
          Income
        </span>
        <span className="legend__item">
          <span className="legend__swatch" style={{ background: COLORS.spending }} />
          Spending
        </span>
        {partialRow && (
          <span className="legend__item legend__item--soft">
            <span className="legend__hollow" />
            Dashed line and hollow point: month in progress
          </span>
        )}
        {selectedInRange && (
          <span className="legend__note">Grey line marks the selected month</span>
        )}
      </div>
    </div>
  );
}
