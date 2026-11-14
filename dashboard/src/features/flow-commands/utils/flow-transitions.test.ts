import { commandsAllowedIn } from './flow-transitions';

describe('commandsAllowedIn', () => {
  it.each([
    ['fermo', ['start', 'archive']],
    ['attivo', ['pause', 'stop']],
    ['in pausa', ['resume', 'stop']],
    ['archiviato', []],
  ])('offers for a flow %s the commands its status admits', (status, commands) => {
    expect(commandsAllowedIn(status)).toEqual(commands);
  });

  it('offers no command for a status it does not know, leaving the API the authority', () => {
    expect(commandsAllowedIn('sospeso')).toEqual([]);
  });
});
