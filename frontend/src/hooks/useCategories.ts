import { useCallback } from 'react';
import { getCategories } from '../api/categories';
import type { Category, TransactionType } from '../api/types';
import { useApi, type Query } from './useApi';

/** Categories, optionally limited to one type (used by the category picker). */
export function useCategories(type?: TransactionType): Query<Category[]> {
  const fetcher = useCallback((signal: AbortSignal) => getCategories(type, signal), [type]);
  return useApi(fetcher);
}
