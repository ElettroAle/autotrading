import './index.css';

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { startApp } from '@/app';

const container = document.getElementById('root');
if (container !== null) {
  createRoot(container).render(<StrictMode>{await startApp()}</StrictMode>);
}
