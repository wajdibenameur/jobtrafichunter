import { test, expect, Page } from '@playwright/test';
import { readFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';
const config = JSON.parse(readFileSync(process.env['JOBHUNTER_E2E_CONFIG']!, 'utf8')) as {
  email: string;
  password: string;
};
const screenshots = path.resolve('../../.cache/frontend-e2e/screenshots');
mkdirSync(screenshots, { recursive: true });
async function signIn(page: Page): Promise<void> {
  await page.goto('/auth/signin');
  await page.getByLabel('Adresse e-mail', { exact: true }).fill(config.email);
  await page.getByLabel('Mot de passe', { exact: true }).fill(config.password);
  await page.getByRole('button', { name: 'Se connecter', exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

test('profiles, real worker, grouped results, preserved snapshots and mobile', async ({ page }) => {
  await signIn(page);
  await page.evaluate(async () => {
    const sources = [
      '10000000-0000-4000-8000-000000000001',
      '10000000-0000-4000-8000-000000000003',
    ];
    const description =
      'Phase3 synthetic description with Python PostgreSQL services integration testing reliable software delivery teamwork documentation and maintainable APIs. <script>fixture</script>';
    for (let index = 0; index < 2; index++) {
      const jobs: Record<string, unknown>[] = [
        {
          original_url: `https://example.test/phase3/${index}`,
          title: 'Phase3 synthetic Engineer',
          company: 'Synthetic employer',
          city: 'Tunis',
          country: 'Tunisia',
          description,
          published_at: '2026-11-05T12:00:00+00:00',
        },
      ];
      if (index === 0)
        jobs.push(
          {
            original_url: 'https://example.test/phase3/senior',
            title: 'Phase3 synthetic Junior',
            min_years: 5,
          },
          {
            original_url: 'https://example.test/phase3/incomplete',
            title: 'Phase3 synthetic Incomplete',
          },
        );
      const response = await fetch('/api/jobs/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_id: sources[index], jobs, confirm: true }),
      });
      if (!response.ok) throw new Error('Synthetic fixture import failed');
    }
  });
  await page.getByRole('link', { name: 'Profils de recherche', exact: true }).click();
  await page.getByLabel('Nom du profil', { exact: true }).fill('Phase 3 E2E');
  await page.getByRole('checkbox', { name: 'LinkedIn', exact: true }).check();
  await page.getByRole('checkbox', { name: 'Keejob', exact: true }).check();
  await page.getByLabel('Contient au moins un mot-clé', { exact: true }).fill('Phase3 synthetic');
  await page.getByRole('radio', { name: 'Dates avancées', exact: true }).check();
  await page.getByRole('button', { name: 'Enregistrer le profil', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Profil enregistré');
  const original = page
    .locator('.profile-list li')
    .filter({ has: page.getByRole('heading', { name: 'Phase 3 E2E', exact: true }) });
  await original.getByRole('button', { name: 'Dupliquer', exact: true }).click();
  const copy = page
    .locator('.profile-list li')
    .filter({ has: page.getByRole('heading', { name: 'Phase 3 E2E (copie)', exact: true }) });
  await expect(copy).toBeVisible();
  await copy.getByRole('button', { name: 'Retirer', exact: true }).click();
  await expect(copy).toHaveCount(0);
  await original.getByRole('button', { name: 'Modifier', exact: true }).click();
  await expect(page.getByLabel('Contient au moins un mot-clé', { exact: true })).toHaveValue(
    'Phase3 synthetic',
  );
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: path.join(screenshots, 'profiles-desktop.png') });
  await page
    .getByRole('link', { name: 'Rechercher dans mes offres importées', exact: true })
    .click();
  await page
    .getByLabel('Profil à utiliser', { exact: true })
    .selectOption({ label: 'Phase 3 E2E' });
  await page.getByRole('button', { name: 'Lancer la recherche locale', exact: true }).click();
  await expect(page.locator('.execution-panel .badge')).toHaveText('Terminée', { timeout: 20000 });
  const executionURL = page.url();
  await expect(page.locator('.execution-panel .search-metrics strong')).toHaveText([
    '4',
    '1',
    '3',
    '2',
  ]);
  await expect(page.locator('.execution-panel')).toContainText('Collecte externe non exécutée');
  await page.reload();
  await expect(page).toHaveURL(executionURL);
  await expect(page.locator('.execution-panel .search-metrics strong')).toHaveText([
    '4',
    '1',
    '3',
    '2',
  ]);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: path.join(screenshots, 'search-desktop.png') });
  await page
    .locator('.execution-panel')
    .getByRole('link', { name: 'Voir les résultats', exact: true })
    .click();
  await expect(page.locator('.result-row')).toHaveCount(2);
  await expect(
    page.locator('.result-row').filter({ hasText: 'Phase3 synthetic Junior' }),
  ).toHaveCount(0);
  await page
    .getByLabel('Filtrer par titre, entreprise, pays, ville ou domaine', { exact: true })
    .fill('Engineer');
  await page.getByRole('button', { name: 'Filtrer', exact: true }).click();
  await expect(page.locator('.result-row')).toHaveCount(1);
  await page
    .locator('.result-row')
    .getByRole('button', { name: 'Voir le détail', exact: true })
    .click();
  await expect(page.locator('dialog')).toBeVisible();
  await expect(page.locator('dialog')).toContainText('<script>fixture</script>');
  await expect(page.locator('dialog').getByRole('link')).toHaveCount(2);
  await page.screenshot({ path: path.join(screenshots, 'result-detail.png') });
  await page.keyboard.press('Escape');
  await expect(page.locator('dialog')).not.toBeVisible();
  await page.getByRole('button', { name: 'EN', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Results', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'FR', exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(async () => (await page.locator('.sidebar').boundingBox())!.x)
    .toBeLessThanOrEqual(-249);
  await page.evaluate(() => window.scrollTo(0, 0));
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
  ).toBeTruthy();
  await page.screenshot({ path: path.join(screenshots, 'results-mobile.png') });
});

test('missing source is an actionable error and profile data survives reload', async ({ page }) => {
  await signIn(page);
  await page.getByRole('link', { name: 'Profils de recherche', exact: true }).click();
  await page.getByLabel('Nom du profil', { exact: true }).fill('No source E2E');
  await page.getByRole('button', { name: 'Enregistrer le profil', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Profil enregistré');
  await page.reload();
  await expect(page.locator('.profile-list')).toContainText('No source E2E');
  await page
    .getByRole('link', { name: 'Rechercher dans mes offres importées', exact: true })
    .click();
  await page
    .getByLabel('Profil à utiliser', { exact: true })
    .selectOption({ label: 'No source E2E' });
  await page.getByRole('button', { name: 'Lancer la recherche locale', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Choisissez au moins une source');
});
