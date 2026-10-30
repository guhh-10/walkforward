import { request } from './client';
import type { Forecast } from './types';

/** Generates a fresh forecast on the server; nothing is stored. */
export function createForecast(signal?: AbortSignal): Promise<Forecast> {
  return request('/forecasts', { method: 'POST', signal });
}
