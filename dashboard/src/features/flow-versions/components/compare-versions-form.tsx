import { zodResolver } from '@hookform/resolvers/zod';
import { useId } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { FORM_CONTROL } from '@/components/ui/form/form-field';

import type { Version } from '../api/get-flow-versions';

const versionNumber = z.string().regex(/^\d+$/);

const choiceSchema = z.object({ first: versionNumber, second: versionNumber });

type Choice = z.infer<typeof choiceSchema>;

export type ChosenVersions = { readonly first: number; readonly second: number };

type CompareVersionsFormProps = {
  readonly versions: Version[];
  readonly chosen: ChosenVersions | undefined;
  readonly onCompare: (chosen: ChosenVersions) => void;
};

// Without a choice in the address the newest version is proposed against the one before it.
const defaultChoice = (versions: Version[], chosen: ChosenVersions | undefined): Choice => {
  const newest = versions[0]?.version;
  const previous = versions[1]?.version ?? newest;
  return {
    first: textOf(chosen?.first ?? previous),
    second: textOf(chosen?.second ?? newest),
  };
};

const textOf = (number: number | undefined): string => (number === undefined ? '' : String(number));

export const CompareVersionsForm = ({ versions, chosen, onCompare }: CompareVersionsFormProps) => {
  const { register, handleSubmit } = useForm<Choice>({
    resolver: zodResolver(choiceSchema),
    defaultValues: defaultChoice(versions, chosen),
  });
  // With one version there is nothing to compare it with (R6.4.1).
  const alone = versions.length < 2;
  const onlyOneId = useId();
  const options = versions.map((version) => (
    <option key={version.version} value={String(version.version)}>
      {`Versione ${version.version}`}
    </option>
  ));
  return (
    <form
      aria-label="Scelta delle versioni"
      className="flex flex-wrap items-end gap-4"
      onSubmit={handleSubmit((choice) =>
        onCompare({ first: Number(choice.first), second: Number(choice.second) }),
      )}
    >
      <label className="flex flex-col text-sm">
        Prima versione
        <select {...register('first')} className={FORM_CONTROL}>
          {options}
        </select>
      </label>
      <label className="flex flex-col text-sm">
        Seconda versione
        <select {...register('second')} className={FORM_CONTROL}>
          {options}
        </select>
      </label>
      <button
        type="submit"
        disabled={alone}
        aria-describedby={alone ? onlyOneId : undefined}
        className="rounded bg-blue-800 px-4 py-1.5 text-white disabled:opacity-50"
      >
        Confronta
      </button>
      {alone && (
        <p id={onlyOneId} className="text-sm text-slate-600">
          Il confronto serve almeno una seconda versione.
        </p>
      )}
    </form>
  );
};
