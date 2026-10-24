import { useCallback } from 'react';
import { getTransactions } from '../api/transactions';
import type { TransactionPage } from '../api/types';
import { useApi, type Query } from './useApi';

export function useRecentTransactions(limit: number): Query<TransactionPage> {
  const fetcher = useCallback(
    (signal: AbortSignal) => getTransactions({ page: 1, page_size: limit }, signal),
    [limit],
  );
  return useApi(fetcher);
}

/** Number of transactions whose predicted category still awaits confirmation. */
export function useReviewCount(): Query<number> {
  const fetcher = useCallback(
    async (signal: AbortSignal) =>
      (await getTransactions({ status: 'PREDICTED', page_size: 1 }, signal)).total,
    [],
  );
  return useApi(fetcher);
}
