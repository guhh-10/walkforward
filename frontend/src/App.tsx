import { useState } from 'react';
import { AppShell } from './components/AppShell';
import { MonthPicker } from './components/MonthPicker';
import { useHashPage } from './hooks/useHashPage';
import { currentMonth } from './lib/format';
import Dashboard from './pages/Dashboard';
import Forecast from './pages/Forecast';
import ModelEval from './pages/ModelEval';

function App() {
  const page = useHashPage();
  const [month, setMonth] = useState(() => currentMonth());

  return (
    <AppShell
      page={page}
      toolbar={page === 'overview' ? <MonthPicker month={month} onChange={setMonth} /> : null}
    >
      {page === 'overview' && <Dashboard month={month} />}
      {page === 'forecast' && <Forecast />}
      {page === 'model' && <ModelEval />}
    </AppShell>
  );
}

export default App;
