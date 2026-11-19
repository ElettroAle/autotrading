// ADR pannello-del-system-prompt-chiuso (Bug 624): in the form of the flow the system prompt waits in a native
// <details>, closed by default, whose <summary> says whether the flow follows the default; it opens by itself when the
// system prompt is refused, so a refusal never hides in a closed panel.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const FIELD = fileURLToPath(
  new URL('../src/features/flow-editor/components/system-prompt-field.tsx', import.meta.url),
);

const RULES: readonly { readonly breach: string; readonly holds: (source: string) => boolean }[] = [
  { breach: 'non sta in un <details>', holds: (source) => /<details[\s>]/.test(source) },
  {
    breach: 'il pannello è aperto per impostazione predefinita',
    holds: (source) => !/<details[^>]*\sopen(\s|>|=\{true\})/.test(source),
  },
  {
    breach: 'il pannello non si apre da sé su un rifiuto del system prompt',
    holds: (source) =>
      /errors\.system_prompt/.test(source) && /open=\{[^}]*error[^}]*\}/.test(source),
  },
  {
    breach: 'la riga chiusa non dice se il flusso segue il predefinito o un testo personalizzato',
    holds: (source) =>
      /<summary[\s\S]*'predefinito'[\s\S]*'personalizzato'[\s\S]*<\/summary>/.test(source),
  },
];

/** The rules of the ADR the source of the field breaks. */
const breachesOf = (source: string): string[] =>
  RULES.filter((rule) => !rule.holds(source)).map((rule) => rule.breach);

const CONFORMING = `
  const error = errors.system_prompt?.message;
  <details open={opened || error !== undefined} onToggle={toggle}>
    <summary>System prompt <span>{followsDefault ? 'predefinito' : 'personalizzato'}</span></summary>
    <FormField id={FIELD_ID} label="System prompt" error={error}>{textarea}</FormField>
  </details>`;

describe('ADR pannello-del-system-prompt-chiuso: the system prompt in a closed panel of the form of the flow', () => {
  it('is red when the system prompt is always shown', () => {
    expect(breachesOf('<div><FormField error={errors.system_prompt?.message} /></div>')).toContain(
      'non sta in un <details>',
    );
  });

  it('is red when the panel starts open', () => {
    expect(
      breachesOf(
        CONFORMING.replace('<details open={opened || error !== undefined}', '<details open'),
      ),
    ).toEqual([
      'il pannello è aperto per impostazione predefinita',
      'il pannello non si apre da sé su un rifiuto del system prompt',
    ]);
  });

  it('is red when a refusal of the system prompt stays in a closed panel', () => {
    expect(
      breachesOf(CONFORMING.replace('open={opened || error !== undefined}', 'open={opened}')),
    ).toEqual(['il pannello non si apre da sé su un rifiuto del system prompt']);
  });

  it('is red when the closed row does not say whether the flow follows the default', () => {
    expect(
      breachesOf(CONFORMING.replace("{followsDefault ? 'predefinito' : 'personalizzato'}", '')),
    ).toEqual([
      'la riga chiusa non dice se il flusso segue il predefinito o un testo personalizzato',
    ]);
  });

  it('is silent on a closed panel that opens on a refusal and names what the flow follows', () => {
    expect(breachesOf(CONFORMING)).toEqual([]);
  });

  it('finds the field of the system prompt of the dashboard in the closed panel', () => {
    expect(breachesOf(readFileSync(FIELD, 'utf8'))).toEqual([]);
  });
});
