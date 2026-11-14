import { comparisonRows } from './comparison-rows';

describe('comparisonRows', () => {
  it('marks as changed only the parts the API reports, with the values the API gives', () => {
    const rows = comparisonRows(
      [
        { part: 'modello', value: 'a' },
        { part: 'istruzioni', value: 'prudente' },
      ],
      [
        { part: 'modello', value: 'b' },
        { part: 'istruzioni', value: 'prudente' },
      ],
      [{ part: 'modello', before: 'A', after: 'B' }],
    );

    expect(rows).toEqual([
      { part: 'modello', before: 'A', after: 'B', changed: true },
      { part: 'istruzioni', before: 'prudente', after: 'prudente', changed: false },
    ]);
  });

  it('adds at the end a change to a part the dashboard does not list', () => {
    const rows = comparisonRows(
      [{ part: 'modello', value: 'a' }],
      [],
      [{ part: 'nuova parte', before: 'prima', after: 'dopo' }],
    );

    expect(rows).toEqual([
      { part: 'modello', before: 'a', after: '', changed: false },
      { part: 'nuova parte', before: 'prima', after: 'dopo', changed: true },
    ]);
  });
});
