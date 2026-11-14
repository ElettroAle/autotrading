import { setupServer } from 'msw/node';

import { handlers } from './handlers';
import { identityProviderHandlers } from './identity-provider';

export const server = setupServer(...identityProviderHandlers, ...handlers);
