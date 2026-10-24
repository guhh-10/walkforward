import type { ReactNode } from 'react';
import { ApiStatus } from './ApiStatus';
import { MonthPicker } from './MonthPicker';
import { Sidebar } from './Sidebar';

interface AppShellProps {
  month: string;
  onMonthChange: (month: string) => void;
  children: ReactNode;
}

export function AppShell({ month, onMonthChange, children }: AppShellProps) {
  return (
    <div className="shell">
      <Sidebar />
      <div className="shell__main">
        <header className="topbar">
          <div className="topbar__inner">
            <MonthPicker month={month} onChange={onMonthChange} />
            <ApiStatus />
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
