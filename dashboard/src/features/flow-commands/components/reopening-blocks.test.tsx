import { screen, within } from '@testing-library/react';

import { fakePlatform, type FakeFlow } from '@/testing/mocks/platform';
import { renderApp } from '@/testing/test-utils';

const FLOW_PAGE = '/flows/flow-alfa';
const TEXT = 'riaperture short su NEAR ferme fino alle 15:30: 2 perdite consecutive';

// ADR blocco-delle-riaperture-nella-dashboard: the blocks come from the state of the API, with its text, beside the
// suspension of the openings.
describe('ReopeningBlocks', () => {
  let alfa: FakeFlow;

  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    alfa = fakePlatform.addFlow('anna', 'alfa');
  });

  it('shows on the flow every side whose reopenings stop, with the text of the API', async () => {
    alfa.reopeningBlocks = [
      {
        side: 'short',
        asset: 'NEAR',
        consecutive_losses: 2,
        until: '2026-11-26T15:30:00Z',
        text: TEXT,
      },
    ];
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    const blocks = await screen.findByRole('region', { name: 'Riaperture ferme' });
    expect(within(blocks).getByRole('status')).toHaveTextContent(TEXT);
  });

  it('shows nothing for a flow without a block', async () => {
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    await screen.findByRole('group', { name: 'Comandi del flusso' });
    expect(screen.queryByRole('region', { name: 'Riaperture ferme' })).not.toBeInTheDocument();
  });
});
