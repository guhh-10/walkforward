import { request } from './client';
import type { Evaluation } from './types';

export function getLatestEvaluation(signal?: AbortSignal): Promise<Evaluation> {
  return request('/ml/evaluation/latest', { signal });
}
