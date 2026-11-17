import { screen } from '@testing-library/react';

import { fakePlatform } from '@/testing/mocks/platform';
import { renderInApp } from '@/testing/test-utils';

import { useFlows } from '../api/get-flows';

import { FlowOpening } from './flow-opening';

const Probe = ({ flowId }: { flowId: string }) => {
  const read = useFlows().data !== undefined;
  return (
    <>
      <FlowOpening flowId={flowId} />
      {read && <p>flussi letti</p>}
    </>
  );
};

describe('FlowOpening', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addFlow('anna', 'alfa');
    fakePlatform.addFlow('anna', 'bozza', { status: 'bozza', allocatedCapital: null, assets: [] });
    fakePlatform.changeFlow('bozza', { accountId: null });
  });

  it('opens the overview of a draft with what it lacks and the way to its configuration', async () => {
    await renderInApp(<Probe flowId="flow-bozza" />, { account: 'anna' });

    expect(await screen.findByRole('note', { name: 'Da configurare' })).toHaveTextContent(
      "Prima dell'avvio mancano: conto, capitale allocato e asset",
    );
    expect(screen.getByRole('link', { name: 'Configura' })).toHaveAttribute(
      'href',
      '/flows/flow-bozza/edit',
    );
    expect(screen.queryByRole('form')).not.toBeInTheDocument();
  });

  it('opens the overview of a draft with everything assigned with nothing missing', async () => {
    fakePlatform.changeFlow('bozza', {
      accountId: 'account-principale',
      allocatedCapital: 100,
      assets: ['ETH'],
    });
    await renderInApp(<Probe flowId="flow-bozza" />, { account: 'anna' });

    expect(await screen.findByRole('note', { name: 'Da configurare' })).toHaveTextContent(
      'Pronta per essere avviata',
    );
  });

  it('opens the overview of a flow that runs with its results', async () => {
    await renderInApp(<Probe flowId="flow-alfa" />, { account: 'anna' });

    expect(
      await screen.findByRole('region', { name: 'Riepilogo dei risultati' }),
    ).toBeInTheDocument();
    expect(screen.queryByRole('note', { name: 'Da configurare' })).not.toBeInTheDocument();
  });

  it('shows nothing for a flow the user does not have', async () => {
    await renderInApp(<Probe flowId="flow-omega" />, { account: 'anna' });

    await screen.findByText('flussi letti');
    expect(screen.queryByRole('note', { name: 'Da configurare' })).not.toBeInTheDocument();
    expect(
      screen.queryByRole('region', { name: 'Riepilogo dei risultati' }),
    ).not.toBeInTheDocument();
  });
});
