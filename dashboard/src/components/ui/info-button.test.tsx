import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { InfoButton, InfoProvider } from './info-button';

const STOP = 'Distanza dello stop loss dal prezzo d’ingresso. Da 0,1 a 50. Predefinito: 5.';
const CONFIDENCE =
  'Confidenza sotto la quale un’apertura non viene eseguita. Vuoto: ogni apertura passa.';

const Fields = () => (
  <div>
    <p>Fuori dal testo</p>
    <div className="flex flex-wrap">
      <label htmlFor="stop">Stop loss predefinito</label>
      <InfoButton label="Stop loss predefinito" text={STOP} />
      <input id="stop" />
    </div>
    <div className="flex flex-wrap">
      <label htmlFor="confidence">Confidenza minima</label>
      <InfoButton label="Confidenza minima" text={CONFIDENCE} />
      <input id="confidence" />
    </div>
  </div>
);

const button = (label: string) => screen.getByRole('button', { name: `Informazioni su ${label}` });
const shown = (text: string) => screen.queryByText(text);

describe('InfoButton', () => {
  it('is named after the label of its field and keeps its text closed until activated', () => {
    render(<Fields />);

    expect(button('Stop loss predefinito')).toHaveAttribute('aria-expanded', 'false');
    expect(shown(STOP)).not.toBeVisible();
  });

  it('opens the text it controls with a click, and closes it with another', async () => {
    render(<Fields />);

    await userEvent.click(button('Stop loss predefinito'));

    expect(shown(STOP)).toBeVisible();
    expect(button('Stop loss predefinito')).toHaveAttribute('aria-expanded', 'true');
    expect(button('Stop loss predefinito')).toHaveAttribute('aria-controls', shown(STOP)?.id);
    await userEvent.click(button('Stop loss predefinito'));
    expect(shown(STOP)).not.toBeVisible();
  });

  it.each([['{Enter}'], [' ']])('opens with the key %s when it has the focus', async (key) => {
    render(<Fields />);
    button('Stop loss predefinito').focus();

    await userEvent.keyboard(key);

    expect(shown(STOP)).toBeVisible();
  });

  it('closes with Esc and gives the focus back to the button', async () => {
    render(<Fields />);
    await userEvent.click(button('Stop loss predefinito'));

    await userEvent.keyboard('{Escape}');

    expect(shown(STOP)).not.toBeVisible();
    expect(button('Stop loss predefinito')).toHaveFocus();
  });

  it('closes with a click outside the text, and stays open with a click on the text', async () => {
    render(<Fields />);
    await userEvent.click(button('Stop loss predefinito'));

    await userEvent.click(screen.getByText(STOP));
    expect(shown(STOP)).toBeVisible();
    await userEvent.click(screen.getByText('Fuori dal testo'));
    expect(shown(STOP)).not.toBeVisible();
  });

  it('waits for the whole click outside, not the press, so the fields do not move under the pointer', async () => {
    const user = userEvent.setup();
    render(<Fields />);
    await user.click(button('Stop loss predefinito'));

    await user.pointer({ keys: '[MouseLeft>]', target: screen.getByText('Fuori dal testo') });
    expect(shown(STOP)).toBeVisible();
    await user.pointer({ keys: '[/MouseLeft]', target: screen.getByText('Fuori dal testo') });
    expect(shown(STOP)).not.toBeVisible();
  });

  it('ignores Esc and clicks while closed', async () => {
    render(<Fields />);

    await userEvent.keyboard('{Escape}');
    await userEvent.click(screen.getByText('Fuori dal testo'));

    expect(shown(STOP)).not.toBeVisible();
    expect(button('Stop loss predefinito')).not.toHaveFocus();
  });

  it('keeps one text open at a time in the page', async () => {
    render(
      <InfoProvider>
        <Fields />
      </InfoProvider>,
    );
    await userEvent.click(button('Stop loss predefinito'));
    button('Confidenza minima').focus();

    await userEvent.keyboard('{Enter}');

    expect(shown(CONFIDENCE)).toBeVisible();
    expect(shown(STOP)).not.toBeVisible();
    expect(button('Stop loss predefinito')).toHaveAttribute('aria-expanded', 'false');
  });
});
