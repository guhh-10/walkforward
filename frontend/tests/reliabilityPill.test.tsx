import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ReliabilityPill } from '../src/components/ReliabilityPill';

describe('ReliabilityPill', () => {
  it('warns when the forecast is low reliability', () => {
    render(<ReliabilityPill reliability="low" />);
    expect(screen.getByText('Low reliability')).toHaveClass('pill--warning');
  });

  it('is neutral for medium reliability', () => {
    render(<ReliabilityPill reliability="medium" />);
    expect(screen.getByText('Medium reliability')).toHaveClass('pill--neutral');
  });

  it('is positive for high reliability', () => {
    render(<ReliabilityPill reliability="high" />);
    expect(screen.getByText('High reliability')).toHaveClass('pill--positive');
  });
});
