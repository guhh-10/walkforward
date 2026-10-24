import { request } from './client';
import type { TransactionPage, TransactionQuery } from './types';

export function getTransactions(
  query: TransactionQuery = {},
  signal?: AbortSignal,
): Promise<TransactionPage> {
  return request('/transactions', { params: { ...query }, signal });
}
