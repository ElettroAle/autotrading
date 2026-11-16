import { DETAIL_VALUE } from '@/components/ui/details-list';
import type { DeclaredField } from '@/components/ui/form/declared-fields';

type PublicFieldsProps = {
  readonly fields: readonly DeclaredField[];
  readonly values: Readonly<Record<string, string>>;
};

/**
 * The public fields of an account, as the account address, with the labels its exchange gives them: kept in clear and
 * shown, they cannot be replaced (Bug 401). A field the exchange no longer declares is shown by its name.
 */
export const PublicFields = ({ fields, values }: PublicFieldsProps) => {
  const shown = Object.entries(values);
  if (shown.length === 0) {
    return null;
  }
  return (
    <dl className="space-y-1 text-sm">
      {shown.map(([name, value]) => (
        <div key={name}>
          <dt className="text-slate-600">
            {fields.find((field) => field.name === name)?.label ?? name}
          </dt>
          <dd className={`${DETAIL_VALUE} font-mono`}>{value}</dd>
        </div>
      ))}
    </dl>
  );
};
