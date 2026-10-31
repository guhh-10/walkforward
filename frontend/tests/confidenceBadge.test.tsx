import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ConfidenceBadge } from '../src/components/ConfidenceBadge';

describe('ConfidenceBadge', () => {
  it('shows a high-confidence prediction as positive', () => {
    render(<ConfidenceBadge confidence={0.92} />);
    const badge = screen.getByTitle('Model confidence: Confident');
    expect(badge).toHaveClass('pill--positive');
    expect(badge).toHaveTextContent('92%');
  });

  it('treats the 0.8 boundary as confident', () => {
    render(<ConfidenceBadge confidence={0.8} />);
    expect(screen.getByTitle('Model confidence: Confident')).toBeInTheDocument();
  });

  it('shows a middling prediction as fairly sure', () => {
    render(<ConfidenceBadge confidence={0.5} />);
    expect(screen.getByTitle('Model confidence: Fairly sure')).toHaveClass('pill--warning');
  });

  it('flags a low-confidence prediction for review', () => {
    render(<ConfidenceBadge confidence={0.2} />);
    const badge = screen.getByTitle('Model confidence: Needs review');
    expect(badge).toHaveClass('pill--negative');
    expect(badge).toHaveTextContent('Needs review');
  });
});
