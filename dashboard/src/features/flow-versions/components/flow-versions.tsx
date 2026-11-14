import { useSearchParams } from 'react-router';

import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';

import { useFlowVersions } from '../api/get-flow-versions';

import { CompareVersionsForm, type ChosenVersions } from './compare-versions-form';
import { VersionsComparison } from './versions-comparison';
import { VersionsList } from './versions-list';

const VERSION_NUMBER = /^\d+$/;

// The choice lives in the address, so a comparison can be reopened as it is.
const chosenIn = (searchParams: URLSearchParams): ChosenVersions | undefined => {
  const first = searchParams.get('first') ?? '';
  const second = searchParams.get('second') ?? '';
  if (!VERSION_NUMBER.test(first) || !VERSION_NUMBER.test(second)) {
    return undefined;
  }
  return { first: Number(first), second: Number(second) };
};

export const FlowVersions = ({ flowId }: { flowId: string }) => {
  const versions = useFlowVersions(flowId);
  const [searchParams, setSearchParams] = useSearchParams();
  const chosen = chosenIn(searchParams);
  if (versions.isPending) {
    return <Loading />;
  }
  // A failed rereading keeps the data already read on the page: the warning is the page's (ADR 0119).
  if (versions.data === undefined) {
    return <ErrorMessage error={versions.error} />;
  }
  return (
    <div className="space-y-6">
      <VersionsList versions={versions.data} />
      <CompareVersionsForm
        versions={versions.data}
        chosen={chosen}
        onCompare={(choice) =>
          setSearchParams({ first: String(choice.first), second: String(choice.second) })
        }
      />
      {chosen && <VersionsComparison flowId={flowId} chosen={chosen} />}
    </div>
  );
};
