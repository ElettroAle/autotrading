import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';

import { pageDataQuery, queryConfig } from '@/lib/react-query';

import { usePageData } from './use-page-data';

type Answer = { readonly fails: boolean; readonly value: string };

const setUp = () => {
  const answers = { flows: { fails: false, value: 'v1' } as Answer, identity: 0 };
  const queryClient = new QueryClient({ defaultOptions: queryConfig });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  const usePage = () => {
    useQuery({
      queryKey: ['identity'],
      queryFn: () => {
        answers.identity += 1;
        return 'anna';
      },
    });
    const flows = useQuery({
      ...pageDataQuery('flows'),
      queryFn: () =>
        answers.flows.fails
          ? Promise.reject(new Error('non risponde'))
          : Promise.resolve(answers.flows.value),
    });
    return { flows, page: usePageData() };
  };
  return { answers, queryClient, ...renderHook(usePage, { wrapper }) };
};

describe('usePageData', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('dates the data of the page at its last reading', async () => {
    vi.useFakeTimers({ toFake: ['Date'], now: new Date(2026, 10, 14, 10, 0, 0) });
    const { result } = setUp();

    await waitFor(() => expect(result.current.flows.data).toBe('v1'));

    expect(result.current.page.updatedAt).toBe(new Date(2026, 10, 14, 10, 0, 0).getTime());
    expect(result.current.page.stale).toBe(false);
  });

  it('knows no reading before the data of the page arrives', () => {
    const { result } = setUp();

    expect(result.current.page.updatedAt).toBe(0);
  });

  it('rereads the data of the page, and only that, on request', async () => {
    vi.useFakeTimers({ toFake: ['Date'], now: new Date(2026, 10, 14, 10, 0, 0) });
    const { result, answers } = setUp();
    await waitFor(() => expect(result.current.flows.data).toBe('v1'));
    answers.flows = { fails: false, value: 'v2' };
    vi.setSystemTime(new Date(2026, 10, 14, 10, 0, 12));

    await act(() => result.current.page.refresh());

    expect(result.current.flows.data).toBe('v2');
    expect(result.current.page.updatedAt).toBe(new Date(2026, 10, 14, 10, 0, 12).getTime());
    expect(answers.identity).toBe(1);
  });

  it('marks the data of the page as stale when a rereading fails, keeping the last data', async () => {
    const { result, answers } = setUp();
    await waitFor(() => expect(result.current.flows.data).toBe('v1'));
    const firstReading = result.current.page.updatedAt;
    answers.flows = { fails: true, value: 'v2' };

    await act(() => result.current.page.refresh());

    expect(result.current.page.stale).toBe(true);
    expect(result.current.flows.data).toBe('v1');
    expect(result.current.page.updatedAt).toBe(firstReading);
  });

  it('is fresh again once a rereading succeeds', async () => {
    const { result, answers } = setUp();
    await waitFor(() => expect(result.current.flows.data).toBe('v1'));
    answers.flows = { fails: true, value: 'v2' };
    await act(() => result.current.page.refresh());
    answers.flows = { fails: false, value: 'v3' };

    await act(() => result.current.page.refresh());

    expect(result.current.page.stale).toBe(false);
    expect(result.current.flows.data).toBe('v3');
  });

  it('does not count a first reading that failed as stale data: there is nothing to keep', async () => {
    const { result, answers, queryClient } = setUp();
    answers.flows = { fails: true, value: 'v1' };
    await act(() => queryClient.resetQueries());

    await waitFor(() => expect(result.current.flows.isError).toBe(true));

    expect(result.current.page.stale).toBe(false);
  });
});
