import { commandsAllowedIn, isArchivable, operatingCommandsIn } from './flow-transitions';

describe('commandsAllowedIn', () => {
  it.each([
    ['bozza', ['start', 'archive']],
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

// ADR impostazioni-del-flusso-dall-ingranaggio: the page of the flow keeps the commands of every day, the settings keep
// Archivia.
describe('operatingCommandsIn', () => {
  it.each([
    ['fermo', ['start']],
    ['attivo', ['pause', 'stop']],
    ['in pausa', ['resume', 'stop']],
    ['archiviato', []],
  ])('offers for a flow %s the commands of every day, never Archivia', (status, commands) => {
    expect(operatingCommandsIn(status)).toEqual(commands);
  });
});

describe('isArchivable', () => {
  it.each([
    ['bozza', true],
    ['fermo', true],
    ['attivo', false],
    ['in pausa', false],
    ['archiviato', false],
    ['sospeso', false],
  ])('says whether a flow %s can be archived', (status, archivable) => {
    expect(isArchivable(status)).toBe(archivable);
  });
});
