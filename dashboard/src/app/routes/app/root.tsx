import { Outlet } from 'react-router';

import { AccessGate } from '@/features/access/components/access-gate';
import { ProtectedRoute } from '@/lib/auth';

export const AppRoot = () => (
  <ProtectedRoute>
    <AccessGate>
      <Outlet />
    </AccessGate>
  </ProtectedRoute>
);
