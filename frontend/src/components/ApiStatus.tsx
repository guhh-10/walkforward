import { useHealth } from '../hooks/useHealth';

export function ApiStatus() {
  const health = useHealth();

  let tone = 'neutral';
  let label = 'Checking API…';
  if (health.data) {
    tone = 'positive';
    label = 'API connected';
  } else if (health.error) {
    tone = 'negative';
    label = 'API offline';
  }

  return (
    <span className={`pill pill--${tone}`} role="status" title={health.error?.message}>
      <span className="dot" />
      {label}
    </span>
  );
}
