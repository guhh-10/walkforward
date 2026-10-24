import { useState } from 'react';
import { AppShell } from './components/AppShell';
import { currentMonth } from './lib/format';
import Dashboard from './pages/Dashboard';

function App() {
  const [month, setMonth] = useState(() => currentMonth());

  return (
    <AppShell month={month} onMonthChange={setMonth}>
      <Dashboard month={month} />
    </AppShell>
  );
}

export default App;
