import { formatPercent } from '../lib/format';

/** §8.4 confidence tiers: presentation-only, no auto-rejection. */
function tierOf(confidence: number): { tone: string; label: string } {
  if (confidence >= 0.8) return { tone: 'positive', label: 'Confident' };
  if (confidence >= 0.5) return { tone: 'warning', label: 'Fairly sure' };
  return { tone: 'negative', label: 'Needs review' };
}

export function ConfidenceBadge({ confidence }: { confidence: number }) {
  const { tone, label } = tierOf(confidence);
  return (
    <span className={`pill pill--${tone}`} title={`Model confidence: ${label}`}>
      {formatPercent(confidence * 100, 0)} · {label}
    </span>
  );
}
