import type { ReactNode } from 'react';
import type { Query } from '../hooks/useApi';
import { Icon } from './Icon';

interface AsyncProps<T> {
  query: Query<T>;
  /** Height of the loading placeholder, in px. */
  minHeight?: number;
  children: (data: T) => ReactNode;
}

function ErrorState({ error, onRetry }: { error: Error; onRetry: () => void }) {
  return (
    <div className="card state-error" role="alert">
      <Icon name="error" size={22} />
      <div className="state-error__text">
        <strong>Something went wrong</strong>
        <span>{error.message}</span>
      </div>
      <button type="button" className="btn" onClick={onRetry}>
        Retry
      </button>
    </div>
  );
}

/** Renders loading, error, or the data; dims the content while a refresh is in flight. */
export function Async<T>({ query, minHeight = 120, children }: AsyncProps<T>) {
  if (query.data === null) {
    if (query.error) return <ErrorState error={query.error} onRetry={query.reload} />;
    return (
      <div className="skeleton" style={{ minHeight }} role="status" aria-busy="true">
        <span className="sr-only">Loading…</span>
      </div>
    );
  }
  return (
    <div className={query.loading ? 'async async--stale' : 'async'}>{children(query.data)}</div>
  );
}
