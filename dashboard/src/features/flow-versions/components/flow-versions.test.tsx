import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakePlatform, versionsWith } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const OPENROUTER = 'openrouter/deepseek-chat';
const ANTHROPIC = 'anthropic/claude-haiku';
const VERSIONS_URL = '/flows/flow-alfa/versions';

const compare = async (first: string, second: string) => {
  const user = userEvent.setup();
  await user.selectOptions(await screen.findByLabelText('Prima versione'), first);
  await user.selectOptions(screen.getByLabelText('Seconda versione'), second);
  await user.click(screen.getByRole('button', { name: 'Confronta' }));
};

describe('FlowVersions', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addFlow('anna', 'alfa', {
      versions: versionsWith(
        { model: OPENROUTER },
        { instructions: 'prudente' },
        { model: ANTHROPIC },
      ),
    });
  });

  it('lists the versions newest first, each with the date and time it was saved', async () => {
    await renderApp({ account: 'anna', url: VERSIONS_URL });

    const items = within(await screen.findByRole('list', { name: 'Versioni' })).getAllByRole(
      'listitem',
    );
    expect(items.map((item) => item.textContent?.split(' · ')[0])).toEqual([
      'Versione 3',
      'Versione 2',
      'Versione 1',
    ]);
    const times = items.map((item) => within(item).getByText(/\d{4}, \d{2}:\d{2}:\d{2}$/));
    expect(times.map((time) => time.getAttribute('datetime'))).toEqual([
      '2026-11-03T09:30:00.000Z',
      '2026-11-02T09:30:00.000Z',
      '2026-11-01T09:30:00.000Z',
    ]);
  });

  it('proposes the two newest versions to compare', async () => {
    await renderApp({ account: 'anna', url: VERSIONS_URL });

    expect(await screen.findByLabelText('Prima versione')).toHaveValue('2');
    expect(screen.getByLabelText('Seconda versione')).toHaveValue('3');
  });

  it('shows two versions side by side, highlighting only what changed from one to the other', async () => {
    const { router } = await renderApp({ account: 'anna', url: VERSIONS_URL });

    await compare('2', '3');

    const comparison = await screen.findByRole('table', { name: 'Confronto delle versioni' });
    expect(router.state.location.search).toBe('?first=2&second=3');
    expect(
      within(comparison)
        .getAllByRole('columnheader')
        .map((header) => header.textContent),
    ).toEqual(['Campo', 'Versione 2', 'Versione 3']);
    expect(
      within(comparison)
        .getAllByRole('mark')
        .map((mark) => mark.textContent),
    ).toEqual([OPENROUTER, ANTHROPIC]);
    const model = within(comparison).getByRole('row', { name: /^modello/ });
    expect(within(model).getAllByRole('mark')).toHaveLength(2);
    expect(
      within(comparison).getByRole('row', { name: 'istruzioni prudente prudente' }),
    ).toBeVisible();
    expect(screen.queryByText('Nessuna differenza')).not.toBeInTheDocument();
  });

  it('says there is no difference when a version is compared with itself', async () => {
    await renderApp({ account: 'anna', url: `${VERSIONS_URL}?first=3&second=3` });

    expect(await screen.findByText('Nessuna differenza')).toHaveAttribute('role', 'status');
    const comparison = screen.getByRole('table', { name: 'Confronto delle versioni' });
    expect(within(comparison).queryAllByRole('mark')).toHaveLength(0);
  });

  it('shows a change the API reports even for a part the dashboard does not list', async () => {
    server.use(
      http.get('*/flows/:flowId/versions/:first/differences/:second', () =>
        HttpResponse.json([{ part: 'nuova parte', before: 'prima', after: 'dopo' }]),
      ),
    );
    await renderApp({ account: 'anna', url: `${VERSIONS_URL}?first=1&second=2` });

    const comparison = await screen.findByRole('table', { name: 'Confronto delle versioni' });
    expect(within(comparison).getByRole('row', { name: 'nuova parte prima dopo' })).toBeVisible();
  });

  it('ignores a comparison asked in the address without two version numbers', async () => {
    await renderApp({ account: 'anna', url: `${VERSIONS_URL}?first=2&second=ultima` });

    expect(await screen.findByRole('list', { name: 'Versioni' })).toBeVisible();
    expect(
      screen.queryByRole('table', { name: 'Confronto delle versioni' }),
    ).not.toBeInTheDocument();
  });

  it('tells why the versions could not be read', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-omega/versions' });

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Impossibile leggere i dati: flusso non trovato',
    );
  });

  it('tells why the comparison could not be read', async () => {
    await renderApp({ account: 'anna', url: `${VERSIONS_URL}?first=1&second=9` });

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Impossibile leggere i dati: versione di configurazione non trovata: 9',
    );
  });
});
