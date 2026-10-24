import { useCallback } from 'react';
import { getMonthlySummary, getTrends } from '../api/summary';
import type { MonthlySummary, TrendPoint } from '../api/types';
import { useApi, type Query } from './useApi';

export function useMonthlySummary(month: string): Query<MonthlySummary> {
  const fetcher = useCallback((signal: AbortSignal) => getMonthlySummary(month, signal), [month]);
  return useApi(fetcher);
}

export function useTrends(months: number): Query<TrendPoint[]> {
  const fetcher = useCallback((signal: AbortSignal) => getTrends(months, signal), [months]);
  return useApi(fetcher);
}
