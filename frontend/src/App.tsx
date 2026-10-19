import { useEffect, useState } from 'react';
import { getHealth } from './api/client';

function App() {
  const [status, setStatus] = useState('Checking API...');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHealth()
      .then((result) => setStatus(result.status))
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Unknown error');
      });
  }, []);

  return (
    <main>
      <h1>Personal Finance Tracker</h1>
      <p>Frontend: Running</p>
      <p>Backend: {error ?? status}</p>
    </main>
  );
}

export default App;
