import { render, screen } from '@testing-library/react';

import { EnvironmentBadge } from './environment-badge';

describe('EnvironmentBadge', () => {
  it('names the environment of the installation', () => {
    render(<EnvironmentBadge environment="dev" />);

    expect(screen.getByLabelText("Ambiente dell'installazione")).toHaveTextContent('dev');
  });

  it('marks the production installation apart from the others', () => {
    render(
      <>
        <EnvironmentBadge environment="prod" />
        <EnvironmentBadge environment="dev" />
      </>,
    );

    const [production, development] = screen.getAllByLabelText("Ambiente dell'installazione");
    expect(production).toHaveClass('bg-red-700');
    expect(development).not.toHaveClass('bg-red-700');
  });
});
