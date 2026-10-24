import { getHealth } from '../api/client';
import { useApi, type Fetcher, type Query } from './useApi';

const fetchHealth: Fetcher<{ status: string }> = (signal) => getHealth(signal);

export function useHealth(): Query<{ status: string }> {
  return useApi(fetchHealth);
}
