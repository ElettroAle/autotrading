import { screen } from '@testing-library/react';

import { fakePlatform } from '@/testing/mocks/platform';
import { renderApp, renderInApp } from '@/testing/test-utils';

import { useFlows } from '../api/get-flows';

import { useFlowTitle } from './use-flow-title';

const Probe = ({ flowId, subject }: { flowId: string; subject?: string }) => {
  const read = useFlows().data !== undefined;
  return (
    <>
      <output aria-label="titolo">{useFlowTitle(flowId, subject)}</output>
      {read && <p>flussi letti</p>}
    </>
  );
};

const title = () => screen.getByLabelText('titolo');

describe('useFlowTitle', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addFlow('anna', 'alfa');
  });

  it('titles the page of the flow with its name once read', async () => {
    await renderInApp(<Probe flowId="flow-alfa" />, { account: 'anna' });

    expect(title()).toHaveTextContent(/^Flusso$/);
    expect(await screen.findByText('alfa')).toBe(title());
  });

  it('titles a page of the flow with what it shows and the name of the flow', async () => {
    await renderInApp(<Probe flowId="flow-alfa" subject="Cicli" />, { account: 'anna' });

    expect(title()).toHaveTextContent('Cicli del flusso');
    expect(await screen.findByText('Cicli di alfa')).toBe(title());
  });

  it('keeps the subject alone for a flow the user does not have', async () => {
    await renderInApp(<Probe flowId="flow-omega" subject="Cicli" />, { account: 'anna' });

    await screen.findByText('flussi letti');
    expect(title()).toHaveTextContent('Cicli del flusso');
  });

  it.each([
    ['/flows/flow-alfa/cycles', 'Cicli di alfa'],
    ['/flows/flow-alfa/positions', 'Posizioni aperte di alfa'],
    ['/flows/flow-alfa/closed-positions', 'Posizioni chiuse di alfa'],
    ['/flows/flow-alfa/versions', 'Versioni della configurazione di alfa'],
    ['/flows/flow-alfa/edit', 'Configurazione di alfa'],
  ])('names the flow in the title of %s', async (url, expected) => {
    await renderApp({ account: 'anna', url });

    expect(await screen.findByRole('heading', { level: 1, name: expected })).toBeInTheDocument();
  });
});
