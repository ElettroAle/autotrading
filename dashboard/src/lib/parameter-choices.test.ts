import {
  admittedChoicesOf,
  choiceOptionsOf,
  defaultChoiceLabelOf,
  hasChoices,
  isAmongChoices,
} from './parameter-choices';

const HORIZON = {
  default: 0,
  choices: [
    { value: 0, label: 'nessuno' },
    { value: 1440, label: '1 giorno' },
  ],
};
const RANGE = { default: 10, choices: [] };

describe('the choices of a parameter of the catalog (ADR orizzonti-lunghi-del-forecast)', () => {
  it('tells a parameter with choices from one that admits its whole range', () => {
    expect([hasChoices(HORIZON), hasChoices(RANGE)]).toEqual([true, false]);
  });

  it('offers every choice by its label, with its value as text', () => {
    expect(choiceOptionsOf(HORIZON)).toEqual([
      { value: '0', label: 'nessuno' },
      { value: '1440', label: '1 giorno' },
    ]);
  });

  it('names the default by its label, or by its value when no choice has it', () => {
    expect(defaultChoiceLabelOf(HORIZON)).toBe('nessuno');
    expect(defaultChoiceLabelOf({ default: 7, choices: HORIZON.choices })).toBe('7');
  });

  it('accepts only the values of its choices', () => {
    expect([isAmongChoices(HORIZON, 1440), isAmongChoices(HORIZON, 60)]).toEqual([true, false]);
  });

  it('says the choices admitted by their labels', () => {
    expect(admittedChoicesOf(HORIZON)).toBe('ammessi nessuno, 1 giorno');
  });
});
