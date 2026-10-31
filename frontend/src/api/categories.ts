import { request } from './client';
import type { Category, TransactionType } from './types';

export function getCategories(type?: TransactionType, signal?: AbortSignal): Promise<Category[]> {
  return request('/categories', { params: { type }, signal });
}
