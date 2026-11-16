import { Given } from './fixtures';

const SCREEN_HEIGHT = 800;

// Shared by the requirements of the dashboard on a phone (R6.4.1, R6.4.5).
Given('uno schermo largo {int} pixel', async ({ dashboard }, width: number) => {
  await dashboard.page.setViewportSize({ width, height: SCREEN_HEIGHT });
});
