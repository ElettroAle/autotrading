import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider, useLocation } from 'react-router';

import { useComparedFlows } from './use-compared-flows';

// The button compares two flows in one click, before the page can show the first.
const Probe = () => {
  const [flowIds, toggle] = useComparedFlows();
  const { search } = useLocation();
  return (
    <>
      <output aria-label="query string">{search}</output>
      <output aria-label="flussi letti">{JSON.stringify(flowIds)}</output>
      <button
        type="button"
        onClick={() => {
          toggle('alfa');
          toggle('beta');
        }}
      >
        Due flussi
      </button>
    </>
  );
};

const openAt = (url: string) => {
  const router = createMemoryRouter([{ path: '/ranking', element: <Probe /> }], {
    initialEntries: [url],
  });
  render(<RouterProvider router={router} />);
};

describe('useComparedFlows', () => {
  it('reads the compared flows of the query string', () => {
    openAt('/ranking?flow=alfa');

    expect(JSON.parse(screen.getByLabelText('flussi letti').textContent ?? '')).toEqual(['alfa']);
  });

  it('keeps two flows compared before the page shows the first (ADR-0166)', async () => {
    openAt('/ranking');

    await userEvent.click(screen.getByRole('button', { name: 'Due flussi' }));

    expect(
      new URLSearchParams(screen.getByLabelText('query string').textContent).getAll('flow'),
    ).toEqual(['alfa', 'beta']);
  });
});
