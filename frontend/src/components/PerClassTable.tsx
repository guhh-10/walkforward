import type { ClassMetrics } from '../api/types';
import { formatPercent } from '../lib/format';

const LOW_RECALL = 0.3;
const LOW_RECALL_MIN_SUPPORT = 5;

function percent(value: number | null): string {
  return value === null ? '–' : formatPercent(value * 100);
}

export function PerClassTable({ classes }: { classes: ClassMetrics[] }) {
  return (
    <div className="card">
      <div className="card__head">
        <div>
          <h2 className="card__title">Per-category results</h2>
          <p className="card__sub">Precision, recall and F1 on the held-out test set</p>
        </div>
      </div>
      <div className="table-scroll">
        <table className="table">
          <thead>
            <tr>
              <th scope="col">Category</th>
              <th scope="col" className="num">
                Precision
              </th>
              <th scope="col" className="num">
                Recall
              </th>
              <th scope="col" className="num">
                F1
              </th>
              <th scope="col" className="num">
                Support
              </th>
            </tr>
          </thead>
          <tbody>
            {classes.map((c) => {
              const lowRecall =
                c.recall !== null && c.recall < LOW_RECALL && c.support >= LOW_RECALL_MIN_SUPPORT;
              return (
                <tr key={c.category_id} className={c.support === 0 ? 'row--muted' : undefined}>
                  <th scope="row">{c.name}</th>
                  <td className="num">{percent(c.precision)}</td>
                  <td className="num">
                    {lowRecall ? (
                      <span className="pill pill--warning">{percent(c.recall)}</span>
                    ) : (
                      percent(c.recall)
                    )}
                  </td>
                  <td className="num">{percent(c.f1)}</td>
                  <td className="num">{c.support}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
