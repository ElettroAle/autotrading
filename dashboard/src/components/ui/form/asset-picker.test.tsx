import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { useState } from 'react';

import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderInApp } from '@/testing/test-utils';

import { AssetPicker } from './asset-picker';

const ChosenAssets = ({ initial = [] }: { initial?: string[] }) => {
  const [chosen, setChosen] = useState(initial);
  return (
    <form aria-label="Prova">
      <AssetPicker id="assets" chosen={chosen} onChange={setChosen} error={undefined} />
      <output aria-label="Scelti">{chosen.join(',')}</output>
    </form>
  );
};

const field = () => screen.getByLabelText('Asset', { exact: true });
const offered = () => screen.queryByRole('list', { name: 'Asset negoziabili' });
const offeredNames = () =>
  within(screen.getByRole('list', { name: 'Asset negoziabili' }))
    .getAllByRole('button')
    .map((button) => button.textContent);
const chosenLabels = () =>
  within(screen.getByRole('list', { name: 'Asset scelti' }))
    .getAllByRole('listitem')
    .map((item) => item.textContent);

const pick = async (search: string, asset: string) => {
  await userEvent.type(field(), search);
  await userEvent.click(
    within(screen.getByRole('list', { name: 'Asset negoziabili' })).getByRole('button', {
      name: asset,
    }),
  );
};

describe('AssetPicker', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
  });

  it('offers nothing until the user types, then the tradable assets the API lists that match', async () => {
    await renderInApp(<ChosenAssets />, { account: 'anna' });
    await screen.findByLabelText('Asset');

    expect(offered()).toBeNull();
    await userEvent.type(field(), 's');

    expect(offeredNames()).toEqual(['SOL']);
  });

  it('shows the chosen assets as labels the user can remove, and offers them no more', async () => {
    await renderInApp(<ChosenAssets />, { account: 'anna' });
    await screen.findByLabelText('Asset');

    await pick('btc', 'BTC');
    await pick('e', 'ETH');
    expect(chosenLabels()).toEqual(['BTC×', 'ETH×']);
    expect(field()).toHaveValue('');
    await userEvent.type(field(), 'btc');
    expect(offered()).toBeNull();

    await userEvent.click(screen.getByRole('button', { name: 'Togli BTC' }));
    expect(chosenLabels()).toEqual(['ETH×']);
    expect(screen.getByLabelText('Scelti')).toHaveTextContent('ETH');
  });

  it('keeps an asset already chosen even when the exchange no longer lists it', async () => {
    await renderInApp(<ChosenAssets initial={['DOGE']} />, { account: 'anna' });

    expect(await screen.findByRole('button', { name: 'Togli DOGE' })).toBeInTheDocument();
  });

  it('chooses with Enter the asset typed in full or the only one left, and nothing else', async () => {
    await renderInApp(<ChosenAssets />, { account: 'anna' });

    await userEvent.type(await screen.findByLabelText('Asset'), 'eth{Enter}');
    await userEvent.type(field(), 'ol{Enter}');
    await userEvent.type(field(), 'zzz{Enter}');

    expect(chosenLabels()).toEqual(['ETH×', 'SOL×']);
    expect(field()).toHaveValue('zzz');
  });

  it('says why the assets cannot be chosen when the API cannot list them', async () => {
    server.use(
      http.get('*/assets', () =>
        HttpResponse.json(
          { detail: 'exchange non raggiungibile, riprovare' },
          { status: 503, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    );
    await renderInApp(<ChosenAssets />, { account: 'anna' });

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Impossibile leggere gli asset negoziabili: exchange non raggiungibile, riprovare',
    );
    expect(field()).toBeDisabled();
  });

  it('describes the field by the reason its value was refused', async () => {
    const Refused = () => (
      <AssetPicker id="assets" chosen={[]} onChange={() => undefined} error="asset non valido" />
    );
    await renderInApp(<Refused />, { account: 'anna' });

    expect(await screen.findByLabelText('Asset')).toHaveAccessibleDescription('asset non valido');
  });
});
