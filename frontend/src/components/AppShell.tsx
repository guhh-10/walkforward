import type { ReactNode } from 'react';
import type { PageId } from '../hooks/useHashPage';
import { ApiStatus } from './ApiStatus';
import { Sidebar } from './Sidebar';

interface AppShellProps {
  page: PageId;
  /** Page-specific controls shown on the left of the top bar. */
  toolbar?: ReactNode;
  children: ReactNode;
}

export function AppShell({ page, toolbar, children }: AppShellProps) {
  return (
    <div className="shell">
      <Sidebar active={page} />
      <div className="shell__main">
        <header className="topbar">
          <div className="topbar__inner">
            <div>{toolbar}</div>
            <ApiStatus />
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
