import { request } from './client';
import type { MonthlySummary, TrendPoint } from './types';

export function getMonthlySummary(month: string, signal?: AbortSignal): Promise<MonthlySummary> {
  return request('/summary/monthly', { params: { month }, signal });
}

export function getTrends(months: number, signal?: AbortSignal): Promise<TrendPoint[]> {
  return request('/summary/trends', { params: { months }, signal });
}
