import { useSyncExternalStore } from 'react';

export type PageId = 'overview' | 'forecast' | 'model';

function subscribe(onChange: () => void): () => void {
  window.addEventListener('hashchange', onChange);
  return () => window.removeEventListener('hashchange', onChange);
}

const PAGES: Record<string, PageId> = { '#forecast': 'forecast', '#model': 'model' };

/** The current page, taken from the URL hash ('#model'); anything else is the overview. */
export function useHashPage(): PageId {
  const hash = useSyncExternalStore(
    subscribe,
    () => window.location.hash,
    () => '',
  );
  return PAGES[hash] ?? 'overview';
}
