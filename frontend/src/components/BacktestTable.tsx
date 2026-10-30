import type { ModelMetrics } from '../api/types';
import { formatCurrency, formatPercent } from '../lib/format';

const MODEL_NAMES: Record<string, string> = {
  naive: 'Naive (same as last month)',
  ma3: '3-month average',
  ses: 'Exponential smoothing',
};

interface BacktestTableProps {
  perModel: Record<string, ModelMetrics>;
  selected: string;
  errorsUsed: number;
}

export function BacktestTable({ perModel, selected, errorsUsed }: BacktestTableProps) {
  const rows = Object.entries(perModel).sort(([, a], [, b]) => a.mae - b.mae);

  return (
    <div className="card">
      <div className="card__head">
        <div>
          <h2 className="card__title">Why this model</h2>
          <p className="card__sub">
            Each model was tested by predicting every past month from the months before it (
            {errorsUsed} predictions). The lowest average error (MAE) is used for the forecast.
          </p>
        </div>
      </div>
      <div className="table-scroll">
        <table className="table">
          <thead>
            <tr>
              <th scope="col">Model</th>
              <th scope="col" className="num">
                MAE
              </th>
              <th scope="col" className="num">
                RMSE
              </th>
              <th scope="col" className="num">
                MAPE
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([name, m]) => (
              <tr key={name}>
                <th scope="row">
                  {MODEL_NAMES[name] ?? name}
                  {name === selected && <span className="pill pill--positive">Selected</span>}
                </th>
                <td className="num">{formatCurrency(m.mae)}</td>
                <td className="num">{formatCurrency(m.rmse)}</td>
                <td className="num">
                  {m.mape === null ? '–' : formatPercent(m.mape)}
                  {m.mape_excluded > 0 && (
                    <span className="table__note"> ({m.mape_excluded} zero months skipped)</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
