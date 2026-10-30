import type { Reliability } from '../api/types';

const LABELS: Record<Reliability, { text: string; tone: string }> = {
  low: { text: 'Low reliability', tone: 'warning' },
  medium: { text: 'Medium reliability', tone: 'neutral' },
  high: { text: 'High reliability', tone: 'positive' },
};

export function ReliabilityPill({ reliability }: { reliability: Reliability }) {
  const { text, tone } = LABELS[reliability];
  return <span className={`pill pill--${tone}`}>{text}</span>;
}
