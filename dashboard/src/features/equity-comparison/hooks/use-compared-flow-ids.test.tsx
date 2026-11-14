import { renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { MemoryRouter } from 'react-router';

import { MAX_COMPARED_FLOWS, useComparedFlowIds } from './use-compared-flow-ids';

const comparedAt = (url: string): string[] =>
  renderHook(() => useComparedFlowIds(), {
    wrapper: ({ children }: { children: ReactNode }) => (
      <MemoryRouter initialEntries={[url]}>{children}</MemoryRouter>
    ),
  }).result.current;

describe('useComparedFlowIds', () => {
  it('reads the compared flows from the query string, in their order', () => {
    expect(comparedAt('/comparison?period=30d&flow=b&flow=a')).toEqual(['b', 'a']);
  });

  it('keeps the first five flows and never a sixth', () => {
    const flows = ['a', 'b', 'c', 'd', 'e', 'f'].map((id) => `flow=${id}`).join('&');

    expect(comparedAt(`/comparison?${flows}`)).toEqual(['a', 'b', 'c', 'd', 'e']);
    expect(MAX_COMPARED_FLOWS).toBe(5);
  });

  it('compares a flow chosen twice once', () => {
    expect(comparedAt('/comparison?flow=a&flow=a&flow=b')).toEqual(['a', 'b']);
  });

  it('compares nothing without a chosen flow', () => {
    expect(comparedAt('/comparison')).toEqual([]);
  });
});
