import { render, screen } from '@testing-library/react';

import { RuntimeConfigProvider } from '@/config/runtime-config';
import { TEST_CONFIG } from '@/testing/test-utils';

import { PageLayout } from './page-layout';

describe('PageLayout', () => {
  it('shows the title, the content and the environment of the installation', () => {
    render(
      <RuntimeConfigProvider config={{ ...TEST_CONFIG, environment: 'prod' }}>
        <PageLayout title="I tuoi flussi">
          <p>contenuto</p>
        </PageLayout>
      </RuntimeConfigProvider>,
    );

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('I tuoi flussi');
    expect(screen.getByText('contenuto')).toBeInTheDocument();
    expect(screen.getByLabelText("Ambiente dell'installazione")).toHaveTextContent('prod');
  });
});
