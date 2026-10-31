import { request } from './client';
import type { TransactionInput, TransactionOut, TransactionPage, TransactionQuery } from './types';

export function getTransactions(
  query: TransactionQuery = {},
  signal?: AbortSignal,
): Promise<TransactionPage> {
  return request('/transactions', { params: { ...query }, signal });
}

/** Replaces a transaction; the backend derives the classification status. */
export function updateTransaction(
  id: number,
  body: TransactionInput,
  signal?: AbortSignal,
): Promise<TransactionOut> {
  return request(`/transactions/${id}`, { method: 'PUT', body, signal });
}
