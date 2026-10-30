import { createForecast } from '../api/forecast';
import type { Forecast } from '../api/types';
import { useApi, type Fetcher, type Query } from './useApi';

const fetchForecast: Fetcher<Forecast> = (signal) => createForecast(signal);

export function useForecast(): Query<Forecast> {
  return useApi(fetchForecast);
}
