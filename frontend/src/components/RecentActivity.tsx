import type { TransactionPage } from '../api/types';
import { formatDate, formatSigned } from '../lib/format';
import { ConfidenceBadge } from './ConfidenceBadge';
import { Icon } from './Icon';

export function RecentActivity({ page }: { page: TransactionPage }) {
  return (
    <section className="card">
      <div className="card__head">
        <div>
          <h2 className="card__title">Recent activity</h2>
          <p className="card__sub">Latest transactions across all months</p>
        </div>
      </div>

      {page.items.length === 0 ? (
        <p className="empty-note">No transactions recorded yet.</p>
      ) : (
        <ul className="activity">
          {page.items.map((txn) => {
            const isIncome = txn.type === 'income';
            return (
              <li key={txn.id} className="activity__row">
                <div className={`activity__icon activity__icon--${txn.type}`}>
                  <Icon name={isIncome ? 'south_west' : 'north_east'} size={18} />
                </div>
                <div className="activity__main">
                  <div className="activity__title">{txn.description}</div>
                  <div className="activity__meta">
                    {txn.category_name} • {formatDate(txn.date)}
                    {txn.is_future && <span className="pill pill--neutral">Upcoming</span>}
                    {txn.classification?.status === 'PREDICTED' && (
                      <ConfidenceBadge confidence={txn.classification.confidence} />
                    )}
                  </div>
                </div>
                <div className={`activity__amount${isIncome ? ' activity__amount--income' : ''}`}>
                  {formatSigned(isIncome ? txn.amount : -txn.amount)}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
