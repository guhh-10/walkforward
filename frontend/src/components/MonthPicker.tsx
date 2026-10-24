import { currentMonth, formatMonth, shiftMonth } from '../lib/format';
import { Icon } from './Icon';

const EARLIEST_MONTH = '2000-01';

interface MonthPickerProps {
  month: string;
  onChange: (month: string) => void;
}

export function MonthPicker({ month, onChange }: MonthPickerProps) {
  const now = currentMonth();

  return (
    <div className="month-picker">
      <button
        type="button"
        className="icon-btn"
        aria-label="Previous month"
        disabled={month <= EARLIEST_MONTH}
        onClick={() => onChange(shiftMonth(month, -1))}
      >
        <Icon name="chevron_left" />
      </button>
      <span className="month-picker__label" aria-live="polite">
        <Icon name="calendar_month" size={18} />
        {formatMonth(month, 'long')}
      </span>
      <button
        type="button"
        className="icon-btn"
        aria-label="Next month"
        disabled={month >= now}
        onClick={() => onChange(shiftMonth(month, 1))}
      >
        <Icon name="chevron_right" />
      </button>
      {month !== now && (
        <button type="button" className="btn btn--ghost" onClick={() => onChange(now)}>
          This month
        </button>
      )}
    </div>
  );
}
