import { useState } from 'react';
import { AppShell } from './components/AppShell';
import { MonthPicker } from './components/MonthPicker';
import { useHashPage } from './hooks/useHashPage';
import { currentMonth } from './lib/format';
import Dashboard from './pages/Dashboard';
import ModelEval from './pages/ModelEval';

function App() {
  const page = useHashPage();
  const [month, setMonth] = useState(() => currentMonth());

  return (
    <AppShell
      page={page}
      toolbar={page === 'overview' ? <MonthPicker month={month} onChange={setMonth} /> : null}
    >
      {page === 'overview' ? <Dashboard month={month} /> : <ModelEval />}
    </AppShell>
  );
}

export default App;
