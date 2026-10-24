import { useCallback, useEffect, useState } from 'react';

export type Fetcher<T> = (signal: AbortSignal) => Promise<T>;

export interface Query<T> {
  /** Latest successful result; stays populated while the next request is in flight. */
  data: T | null;
  error: Error | null;
  /** True while the current fetcher has not settled yet. */
  loading: boolean;
  reload: () => void;
}

interface Settled<T> {
  source: Fetcher<T>;
  data: T | null;
  error: Error | null;
}

function toError(value: unknown): Error {
  return value instanceof Error ? value : new Error(String(value));
}

/** Runs `fetcher` whenever its identity changes (wrap it in useCallback). */
export function useApi<T>(fetcher: Fetcher<T>): Query<T> {
  const [settled, setSettled] = useState<Settled<T> | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetcher(controller.signal).then(
      (data) => {
        if (!controller.signal.aborted) setSettled({ source: fetcher, data, error: null });
      },
      (err: unknown) => {
        if (!controller.signal.aborted) {
          setSettled({ source: fetcher, data: null, error: toError(err) });
        }
      },
    );
    return () => controller.abort();
  }, [fetcher, attempt]);

  const reload = useCallback(() => setAttempt((n) => n + 1), []);
  const current = settled?.source === fetcher;

  return {
    data: settled?.data ?? null,
    error: current ? settled.error : null,
    loading: !current,
    reload,
  };
}
