import { emptyHistory, fakePlatform } from '@/testing/mocks/platform';

import { Given } from './fixtures';

// Shared by the closed positions (R2.2.5) and the statistics (R2.2.6): the flow closed nothing, neither in the list
// the API pages nor in the history the statistics read.
Given('che il flusso {string} non ha posizioni chiuse', async ({ memory }, flow: string) => {
  fakePlatform.recordClosedPositions(flow, []);
  memory.histories.set(flow, memory.histories.get(flow) ?? emptyHistory());
});
