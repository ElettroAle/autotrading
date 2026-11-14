import { render, screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';

import { server } from '@/testing/mocks/server';
import { TEST_CONFIG } from '@/testing/test-utils';

import {
  isAccessConfigured,
  loadRuntimeConfig,
  RuntimeConfigProvider,
  RuntimeConfigUnavailableError,
  useRuntimeConfig,
} from './runtime-config';

const CONFIG_URL = `http://localhost:3000${import.meta.env.BASE_URL}config.json`;

describe('loadRuntimeConfig', () => {
  it('reads the configuration the container serves beside the dashboard', async () => {
    server.use(http.get(CONFIG_URL, () => HttpResponse.json(TEST_CONFIG)));

    expect(await loadRuntimeConfig()).toEqual(TEST_CONFIG);
  });

  it('fails when the container does not serve it', async () => {
    server.use(http.get(CONFIG_URL, () => new HttpResponse(null, { status: 404 })));

    await expect(loadRuntimeConfig()).rejects.toBeInstanceOf(RuntimeConfigUnavailableError);
  });

  it('fails when the installation does not name its environment', async () => {
    server.use(http.get(CONFIG_URL, () => HttpResponse.json({ ...TEST_CONFIG, environment: '' })));

    await expect(loadRuntimeConfig()).rejects.toBeInstanceOf(RuntimeConfigUnavailableError);
  });
});

describe('isAccessConfigured', () => {
  it('admits the access once issuer, client and scope are configured', () => {
    expect(isAccessConfigured(TEST_CONFIG)).toBe(true);
  });

  it.each(['issuer', 'clientId', 'scope'] as const)(
    'keeps the access closed without the %s',
    (key) => {
      expect(isAccessConfigured({ ...TEST_CONFIG, [key]: '' })).toBe(false);
    },
  );
});

describe('useRuntimeConfig', () => {
  const Environment = () => <p>{useRuntimeConfig().environment}</p>;

  it('gives the configuration of the installation to the pages', () => {
    render(
      <RuntimeConfigProvider config={TEST_CONFIG}>
        <Environment />
      </RuntimeConfigProvider>,
    );

    expect(screen.getByText('dev')).toBeInTheDocument();
  });

  it('fails outside the provider', () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);

    expect(() => render(<Environment />)).toThrow(RuntimeConfigUnavailableError);
  });
});
