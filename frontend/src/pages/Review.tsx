import { useState } from 'react';
import { updateTransaction } from '../api/transactions';
import type { Category, TransactionOut } from '../api/types';
import { Async } from '../components/Async';
import { ConfidenceBadge } from '../components/ConfidenceBadge';
import { Icon } from '../components/Icon';
import { useCategories } from '../hooks/useCategories';
import { useReviewQueue } from '../hooks/useTransactions';
import { formatCurrency, formatDate } from '../lib/format';

const PAGE_SIZE = 10;

function ReviewRow({
  txn,
  categories,
  onReviewed,
}: {
  txn: TransactionOut;
  categories: Category[];
  onReviewed: () => void;
}) {
  const predictedId = txn.classification?.predicted_category_id ?? txn.category_id;
  const [selected, setSelected] = useState(predictedId);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isCorrection = selected !== predictedId;
  const options = categories.filter((c) => c.type === txn.type);

  async function save() {
    setBusy(true);
    setError(null);
    try {
      await updateTransaction(txn.id, {
        amount: txn.amount,
        type: txn.type,
        date: txn.date,
        description: txn.description,
        category_id: selected,
      });
      onReviewed();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save the category.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="review-row">
      <div className="review-row__main">
        <div className="review-row__title">{txn.description}</div>
        <div className="review-row__meta">
          {formatDate(txn.date)} · {formatCurrency(txn.amount)}
        </div>
      </div>

      <div className="review-row__guess">
        <span className="review-row__label">Predicted</span>
        <span className="review-row__category">{txn.classification?.predicted_category}</span>
        {txn.classification && <ConfidenceBadge confidence={txn.classification.confidence} />}
      </div>

      <div className="review-row__action">
        <label className="sr-only" htmlFor={`category-${txn.id}`}>
          Final category
        </label>
        <select
          id={`category-${txn.id}`}
          className="select"
          value={selected}
          disabled={busy}
          onChange={(event) => setSelected(Number(event.target.value))}
        >
          {options.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="btn btn--primary"
          onClick={save}
          disabled={busy || !txn.classification}
        >
          {isCorrection ? 'Save correction' : 'Confirm'}
        </button>
      </div>

      {error && (
        <p className="review-row__error" role="alert">
          {error}
        </p>
      )}
    </li>
  );
}

function EmptyQueue() {
  return (
    <section className="card empty-model">
      <Icon name="task_alt" size={32} className="tone-positive" />
      <h2 className="card__title">Nothing to review</h2>
      <p>
        Every predicted category has been confirmed or corrected. New transactions land here
        automatically while a classifier is trained.
      </p>
    </section>
  );
}

export default function Review() {
  const [page, setPage] = useState(1);
  const queue = useReviewQueue(page, PAGE_SIZE);
  const categories = useCategories();

  const total = queue.data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  // Reviewing the last item of a later page would leave that page empty; step back.
  function reviewedLastOfPage(remaining: number) {
    if (remaining === 0 && page > 1) setPage((current) => current - 1);
    else queue.reload();
  }

  return (
    <div className="dashboard">
      <section className="dashboard__intro">
        <h1>Review queue</h1>
        <p>
          The classifier guessed a category for these transactions. Confirm the guess, or pick the
          right category. Your choices become training data for the next model.
        </p>
      </section>

      <Async query={queue} minHeight={240}>
        {(data) =>
          data.items.length === 0 ? (
            <EmptyQueue />
          ) : (
            <Async query={categories} minHeight={240}>
              {(cats) => (
                <section className="card">
                  <div className="card__head">
                    <div>
                      <h2 className="card__title">Waiting for review</h2>
                      <p className="card__sub">
                        {total} transaction{total === 1 ? '' : 's'}
                      </p>
                    </div>
                  </div>

                  <ul className="review-list">
                    {data.items.map((txn) => (
                      <ReviewRow
                        key={txn.id}
                        txn={txn}
                        categories={cats}
                        onReviewed={() => reviewedLastOfPage(data.items.length - 1)}
                      />
                    ))}
                  </ul>

                  {total > PAGE_SIZE && (
                    <div className="review-pager">
                      <button
                        type="button"
                        className="btn"
                        disabled={page <= 1}
                        onClick={() => setPage((current) => current - 1)}
                      >
                        Previous
                      </button>
                      <span className="card__sub">
                        Page {page} of {pageCount}
                      </span>
                      <button
                        type="button"
                        className="btn"
                        disabled={page >= pageCount}
                        onClick={() => setPage((current) => current + 1)}
                      >
                        Next
                      </button>
                    </div>
                  )}
                </section>
              )}
            </Async>
          )
        }
      </Async>
    </div>
  );
}
