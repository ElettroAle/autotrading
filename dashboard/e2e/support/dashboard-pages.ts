import { expect, type Locator, type Page } from '@playwright/test';

import { accessTokenOf, fakePlatform } from '@/testing/mocks/platform';

const BASE_PATH = '/dashboard';

/** What a user sees and does in the dashboard, so the steps read as the scenario. */
export class DashboardPages {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  async open(path = '/'): Promise<void> {
    await this.page.goto(`${BASE_PATH}${path}`);
  }

  async openNotifications(): Promise<void> {
    await this.open('/notifications');
  }

  async openFlow(name: string): Promise<void> {
    await this.open(`/flows/${encodeURIComponent(fakePlatform.flowNamed(name).id)}`);
  }

  async openPositionsOf(flowName: string): Promise<void> {
    await this.open(`/flows/${fakePlatform.flowNamed(flowName).id}/positions`);
  }

  async openClosedPositionsOf(flowName: string): Promise<void> {
    await this.open(`/flows/${fakePlatform.flowNamed(flowName).id}/closed-positions`);
  }

  async openAccounts(): Promise<void> {
    await this.open('/accounts');
  }

  /** The histories of R2.5.1, with the tab and the filters already in the query string when given. */
  async openHistory(search = ''): Promise<void> {
    await this.open(`/history${search}`);
  }

  async openNewFlow(): Promise<void> {
    await this.open('/flows/new');
  }

  async openFlowEditor(name: string): Promise<void> {
    await this.open(`/flows/${fakePlatform.flowNamed(name).id}/edit`);
  }

  /** A field of a form, by its label: its accessible description is the reason the API refused its value. */
  field(label: string): Locator {
    return this.page.getByLabel(label, { exact: true });
  }

  /** The row of the list of the flows that names the flow. */
  flowInList(name: string): Locator {
    return this.flows()
      .getByRole('listitem')
      .filter({ has: this.page.getByRole('link', { name, exact: true }) });
  }

  async openCyclesOf(flowName: string): Promise<void> {
    await this.open(`/flows/${fakePlatform.flowNamed(flowName).id}/cycles`);
  }

  /** From the page of the flow, as a user gets there. */
  async openVersionsOf(name: string): Promise<void> {
    await this.flows().getByRole('link', { name, exact: true }).click();
    await this.page.getByRole('link', { name: 'Versioni della configurazione' }).click();
    await expect(this.versions()).toBeVisible();
  }

  async compare(first: number, second: number): Promise<void> {
    await this.page.getByLabel('Prima versione').selectOption(String(first));
    await this.page.getByLabel('Seconda versione').selectOption(String(second));
    await this.page.getByRole('button', { name: 'Confronta' }).click();
  }

  /** Signs in from the sign-in page: the account is the one typed on the page of the identity provider. */
  async signInAs(account: string): Promise<void> {
    await expect(this.signInButton()).toBeVisible();
    fakePlatform.signIn(account);
    await this.signInButton().click();
    await this.page.waitForURL((url) => !url.pathname.endsWith('/login'));
  }

  /** Opens the page of a flow as the account: the sign-in brings the user back to the page asked for. */
  async openFlowAs(account: string, name: string): Promise<void> {
    await this.openFlow(name);
    await this.signInAs(account);
    await expect(this.flowName().or(this.page.getByText('Flusso non trovato.'))).toBeVisible();
  }

  /** Asks the API, with the token of the account, for a command the page does not offer. */
  async send(account: string, method: string, path: string): Promise<number> {
    return this.page.evaluate(
      async (request) =>
        (
          await fetch(request.path, {
            method: request.method,
            headers: { Authorization: `Bearer ${request.token}` },
          })
        ).status,
      { token: accessTokenOf(account), method, path },
    );
  }

  async openAndSignInAs(account: string): Promise<void> {
    await this.open();
    await this.signInAs(account);
  }

  signInButton(): Locator {
    return this.page.getByRole('button', { name: 'Accedi' });
  }

  signInHeading(): Locator {
    return this.page.getByRole('heading', { name: 'Accesso alla dashboard' });
  }

  pageHeading(): Locator {
    return this.page.getByRole('heading', { level: 1 });
  }

  environment(): Locator {
    return this.page.getByLabel("Ambiente dell'installazione");
  }

  flows(): Locator {
    return this.page.getByRole('list', { name: 'Flussi' });
  }

  flowLinks(): Locator {
    return this.page.locator(`a[href^="${BASE_PATH}/flows/"]`);
  }

  /** The summary of a flow on the page of the flows, by its name. */
  flowSummary(name: string): Locator {
    return this.page.getByRole('article', { name, exact: true });
  }

  /** One fact of the summary of a flow, by the term it shows: «Stato», «Rendimento», ... */
  flowFact(name: string, term: string): Locator {
    return this.flowSummary(name).getByLabel(term, { exact: true });
  }

  recentOutcomes(name: string): Locator {
    return this.flowSummary(name).getByRole('list', { name: 'Esito degli ultimi cicli' });
  }

  flowName(): Locator {
    return this.page.getByRole('heading', { level: 2 });
  }

  accountRow(name: string): Locator {
    return this.page
      .getByRole('table', { name: 'Conti' })
      .locator('tbody tr')
      .filter({ has: this.page.getByRole('cell', { name, exact: true }) });
  }

  /** The cell of the account under the column with the header, as the table shows it on a wide screen. */
  async accountCell(name: string, header: string): Promise<Locator> {
    await this.accountRow(name).waitFor();
    const headers = await this.page
      .getByRole('table', { name: 'Conti' })
      .getByRole('columnheader')
      .allTextContents();
    return this.accountRow(name).getByRole('cell').nth(headers.indexOf(header));
  }

  registerAccount(): Locator {
    return this.page.getByRole('link', { name: 'Registra un conto' });
  }

  flowStatus(): Locator {
    return this.page.getByText(/^Stato: /);
  }

  /** A command of the flow, by the word the scenarios use for it, whatever its case. */
  flowCommand(name: string): Locator {
    return this.page
      .getByRole('group', { name: 'Comandi del flusso' })
      .getByRole('button', { name: new RegExp(`^${name}$`, 'i') });
  }

  /** The confirmation the dashboard asks before a command, by its title. */
  confirmation(title: string): Locator {
    return this.page.getByRole('group', { name: title });
  }

  cycleRows(): Locator {
    return this.page.getByRole('table', { name: 'Cicli' }).locator('tbody tr');
  }

  openPositionRows(): Locator {
    return this.page.getByRole('table', { name: 'Posizioni aperte' }).locator('tbody tr');
  }

  closedPositionRows(): Locator {
    return this.page.getByRole('table', { name: 'Posizioni chiuse' }).locator('tbody tr');
  }

  /** The cell of a row under the column with the header: every cell carries its header, shown on small screens. */
  cell(row: Locator, header: string): Locator {
    return row.locator('td').filter({ has: this.page.getByText(header, { exact: true }) });
  }

  content(): Locator {
    return this.page.getByRole('main');
  }

  nextPage(): Locator {
    return this.page.getByRole('link', { name: 'Pagina successiva' });
  }

  /** A section of the detail of a cycle, by the title it shows. */
  section(title: string): Locator {
    return this.page.getByRole('group', { name: title, exact: true });
  }

  failure(): Locator {
    return this.page.getByRole('region', { name: 'Errore del ciclo' });
  }

  alert(): Locator {
    return this.page.getByRole('alert');
  }

  /** A message the dashboard tells the user, as an alert or as a status, with exactly this text. */
  message(text: string): Locator {
    return this.page
      .getByRole('alert')
      .or(this.page.getByRole('status'))
      .and(this.page.getByText(text, { exact: true }));
  }

  button(name: string): Locator {
    return this.page.getByRole('button', { name });
  }

  linkCode(): Locator {
    return this.page.getByLabel('Codice di collegamento');
  }

  linkCodeExpiry(): Locator {
    return this.page.getByLabel('Scadenza del codice');
  }

  botLink(): Locator {
    return this.page.getByRole('link', { name: 'Apri il bot e collega la chat' });
  }

  linkedChat(): Locator {
    return this.page.getByLabel('Chat collegata');
  }

  period(): Locator {
    return this.page.getByLabel('Periodo');
  }

  historyTab(name: string): Locator {
    return this.page.getByRole('tab', { name });
  }

  /** A filter of the histories, by the label it shows. */
  filter(label: string): Locator {
    return this.page.getByLabel(label, { exact: true });
  }

  /** The rows of a history, by the name of its table. */
  historyRows(table: string): Locator {
    return this.page
      .getByRole('table', { name: table, exact: true })
      .locator(':scope > tbody > tr');
  }

  statistics(): Locator {
    return this.page.getByRole('region', { name: 'Statistiche' });
  }

  /** The value the statistics panel shows beside a label. */
  statistic(label: string): Locator {
    return this.statistics().getByLabel(label, { exact: true });
  }

  equityCurve(): Locator {
    return this.page.getByRole('figure', { name: 'Equity curve' });
  }

  /** The points of the equity curve: each names its equity, its instant and the area it falls in. */
  equityPoints(): Locator {
    return this.equityCurve().getByRole('img', { name: /^Equity / });
  }

  equityPoint(equity: number): Locator {
    return this.equityCurve().getByRole('img', { name: new RegExp(`^Equity ${equity} del `) });
  }

  versions(): Locator {
    return this.page.getByRole('list', { name: 'Versioni' });
  }

  comparison(): Locator {
    return this.page.getByRole('table', { name: 'Confronto delle versioni' });
  }

  /** The value the page of a flow shows for one part of its configuration. */
  detail(label: string): Locator {
    return this.page
      .getByLabel('Configurazione')
      .locator('dt', { hasText: label })
      .locator('xpath=following-sibling::dd[1]');
  }

  draftLabel(): Locator {
    return this.page.getByText('Bozza', { exact: true });
  }

  status(status: string): Locator {
    return status === 'bozza' ? this.draftLabel() : this.page.getByText(`Stato: ${status}`);
  }

  async command(name: string): Promise<void> {
    await this.page.getByRole('button', { name, exact: true }).click();
  }

  importForm(): Locator {
    return this.page.getByRole('form', { name: 'Importazione di una strategia' });
  }

  /** Imports a strategy file, chosen from the disk of the user, as a new flow with the name. */
  async importStrategy(name: string, file: string): Promise<void> {
    const form = this.importForm();
    await form.getByLabel('Nome del nuovo flusso').fill(name);
    await form.getByLabel('File della strategia').setInputFiles({
      name: 'strategia.json',
      mimeType: 'application/json',
      buffer: Buffer.from(file),
    });
    await form.getByRole('button', { name: 'Importa' }).click();
  }

  /** Exports the strategy of the flow on the page and gives the file the browser saved, with its name. */
  async exportStrategy(): Promise<{ name: string; content: string }> {
    const download = this.page.waitForEvent('download');
    await this.command('Esporta');
    const saved = await download;
    const chunks: Buffer[] = [];
    for await (const chunk of await saved.createReadStream()) {
      chunks.push(Buffer.from(chunk as Uint8Array));
    }
    return { name: saved.suggestedFilename(), content: Buffer.concat(chunks).toString('utf-8') };
  }

  async assign(account: string, capital: string, assets: string): Promise<void> {
    const form = this.page.getByRole('form', { name: 'Assegnazione della bozza' });
    await form.getByLabel('Conto').selectOption({ label: account });
    await form.getByLabel('Capitale allocato (USDC)').fill(capital);
    await form.getByLabel('Asset').fill(assets);
    await form.getByRole('button', { name: 'Assegna' }).click();
  }
}
