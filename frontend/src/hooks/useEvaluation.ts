import { getLatestEvaluation } from '../api/ml';
import type { Evaluation } from '../api/types';
import { useApi, type Fetcher, type Query } from './useApi';

const fetchEvaluation: Fetcher<Evaluation> = (signal) => getLatestEvaluation(signal);

export function useEvaluation(): Query<Evaluation> {
  return useApi(fetchEvaluation);
}
