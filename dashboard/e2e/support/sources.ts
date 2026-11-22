import { FAKE_SOURCES } from '@/testing/mocks/catalogs';
import type { FakeSource } from '@/testing/mocks/platform';
import type { FakeParameterValue } from '@/testing/mocks/source-parameters';

// The forecast is not in the catalog of the fake platform: its flows are written straight in the platform.
const ADAPTER_OUT_OF_THE_CATALOG = 'Prophet';

/**
 * The adapter a source of the specifications is chosen with: the first one the catalog of the fake platform offers, as
 * the specifications written before the adapters name only the source (R4.1.1).
 */
export const adapterOf = (source: string): string =>
  FAKE_SOURCES.find((each) => each.name === source)?.adapters[0]?.name ??
  ADAPTER_OUT_OF_THE_CATALOG;

/** A source of a flow with its adapter, its weight and its parameters, as the fake platform keeps it. */
export const aSource = (
  name: string,
  weight: number,
  parameters?: Readonly<Record<string, FakeParameterValue>>,
): FakeSource => ({
  name,
  adapters: [
    { name: adapterOf(name), weight, ...(parameters === undefined ? {} : { parameters }) },
  ],
});

/** «fonte · adapter», as the dashboard names an adapter of a source (R4.1.1). */
export const labelOf = (source: string): string => `${source} · ${adapterOf(source)}`;

/** The sources of a flow as its configuration shows them: «fonte · adapter (peso N)». */
export const sourcesText = (sources: readonly FakeSource[]): string =>
  sources
    .flatMap((source) =>
      source.adapters.map((adapter) => `${source.name} · ${adapter.name} (peso ${adapter.weight})`),
    )
    .join(', ');
