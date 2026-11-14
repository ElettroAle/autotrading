import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import type { PageData } from '@/hooks/use-page-data';

import { RefreshBar } from './refresh-bar';

const pageData = (data: Partial<PageData> = {}): PageData => ({
  updatedAt: new Date(2026, 10, 14, 10, 0, 30).getTime(),
  stale: false,
  refresh: vi.fn(() => Promise.resolve()),
  ...data,
});

describe('RefreshBar', () => {
  it('tells the instant of the last update of the data', () => {
    render(<RefreshBar pageData={pageData()} />);

    expect(screen.getByText(/^Ultimo aggiornamento:/)).toHaveTextContent(
      'Ultimo aggiornamento: 10:00:30',
    );
  });

  it('tells no instant before the data arrives', () => {
    render(<RefreshBar pageData={pageData({ updatedAt: 0 })} />);

    expect(screen.queryByText(/^Ultimo aggiornamento:/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Aggiorna' })).toBeInTheDocument();
  });

  it('rereads the data when the user presses Aggiorna', async () => {
    const data = pageData();
    render(<RefreshBar pageData={data} />);

    await userEvent.click(screen.getByRole('button', { name: 'Aggiorna' }));

    expect(data.refresh).toHaveBeenCalledOnce();
  });

  it('warns that the data shown is not up to date when a rereading failed', () => {
    render(<RefreshBar pageData={pageData({ stale: true })} />);

    expect(screen.getByRole('alert')).toHaveTextContent('Dati non aggiornati');
  });

  it('warns nothing while the data is up to date', () => {
    render(<RefreshBar pageData={pageData()} />);

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
