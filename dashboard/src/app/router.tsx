import type { RouteObject } from 'react-router';

import { paths } from '@/config/paths';

import { CycleRoute } from './routes/app/cycle';
import { CyclesRoute } from './routes/app/cycles';
import { FlowRoute } from './routes/app/flow';
import { HomeRoute } from './routes/app/home';
import { AppRoot } from './routes/app/root';
import { LoginRoute } from './routes/login';
import { NotFoundRoute } from './routes/not-found';

/** The dashboard lives under /dashboard on the name of the installation, beside the API (ADR 0117). */
export const BASE_NAME = '/dashboard';

export const routes: RouteObject[] = [
  { path: paths.login.path, element: <LoginRoute /> },
  {
    path: paths.home.path,
    element: <AppRoot />,
    children: [
      { index: true, element: <HomeRoute /> },
      { path: paths.flow.path, element: <FlowRoute /> },
      { path: paths.flowCycles.path, element: <CyclesRoute /> },
      { path: paths.cycle.path, element: <CycleRoute /> },
    ],
  },
  { path: '*', element: <NotFoundRoute /> },
];
