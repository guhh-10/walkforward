import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Async } from '../src/components/Async';
import type { Query } from '../src/hooks/useApi';

function query<T>(overrides: Partial<Query<T>>): Query<T> {
  return { data: null, error: null, loading: false, reload: () => {}, ...overrides };
}

describe('Async', () => {
  it('announces loading with a skeleton placeholder', () => {
    render(<Async query={query<string>({ loading: true })}>{() => null}</Async>);
    const skeleton = screen.getByRole('status');
    expect(skeleton).toHaveClass('skeleton');
    expect(skeleton).toHaveTextContent('Loading…');
  });

  it('shows the error and retries on demand', () => {
    const reload = vi.fn();
    render(
      <Async query={query<string>({ error: new Error('Request failed'), reload })}>
        {() => null}
      </Async>,
    );
    expect(screen.getByRole('alert')).toHaveTextContent('Request failed');
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(reload).toHaveBeenCalledOnce();
  });

  it('renders the data once it has settled', () => {
    render(<Async query={query<string>({ data: 'ready' })}>{(value) => <p>{value}</p>}</Async>);
    expect(screen.getByText('ready')).toBeInTheDocument();
  });
});
