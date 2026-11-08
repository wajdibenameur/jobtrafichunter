import { test, expect } from '@playwright/test';
import { readFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';
const config = JSON.parse(readFileSync(process.env['JOBHUNTER_E2E_CONFIG']!, 'utf8')) as {
  email: string;
  password: string;
};
// This shared-schema scenario runs after existing import-count assertions.
const screenshots = path.resolve('../../.cache/frontend-e2e/screenshots');
mkdirSync(screenshots, { recursive: true });

test('scraping page saves real filters, keeps collection disabled and reuses local results', async ({
  page,
}) => {
  test.setTimeout(60000);
  page.setDefaultTimeout(10000);
  await page.goto('/auth/signin');
  await page.getByLabel('Adresse e-mail', { exact: true }).fill(config.email);
  await page.getByLabel('Mot de passe', { exact: true }).fill(config.password);
  await page.getByRole('button', { name: 'Se connecter', exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  const ids = await page.evaluate(async () => {
    const source = await fetch('/api/sources', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'Scraping fixture source',
        homepage: 'https://example.test/scraping-fixture',
        region: 'GLOBAL',
      }),
    });
    if (!source.ok) throw new Error('Synthetic source setup failed');
    const sourceId = (await source.json()).id as string;
    const now = Date.now();
    const imported = await fetch('/api/jobs/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_id: sourceId,
        confirm: true,
        jobs: [
          {
            original_url: 'https://example.test/scraping-fixture/recent',
            title: 'Scraping fixture recent',
            min_years: 0,
            published_at: new Date(now - 30 * 60000).toISOString(),
          },
          {
            original_url: 'https://example.test/scraping-fixture/old',
            title: 'Scraping fixture old',
            min_years: 0,
            published_at: new Date(now - 6 * 3600000).toISOString(),
          },
          {
            original_url: 'https://example.test/scraping-fixture/unknown',
            title: 'Scraping fixture unknown',
            min_years: 0,
          },
        ],
      }),
    });
    if (!imported.ok) throw new Error('Synthetic import setup failed');
    const profile = await fetch('/api/search/profiles', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'Scraping fixture profile',
        description: 'Synthetic only',
        criteria: { source_ids: [sourceId], experience_levels: [], publication_days: 3 },
      }),
    });
    if (!profile.ok) throw new Error('Synthetic profile setup failed');
    return { sourceId, profileId: (await profile.json()).id as string };
  });
  try {
    await page.getByRole('link', { name: 'Scraping', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Scraping', exact: true })).toBeVisible();
    await page
      .getByRole('combobox', { name: 'Profil à utiliser', exact: true })
      .selectOption(ids.profileId);
    await expect(page.getByRole('radio', { name: 'Dates avancées', exact: true })).toBeChecked();
    await expect(
      page.getByRole('button', { name: 'Lancer la recherche', exact: true }),
    ).toBeDisabled();
    await expect(page.getByRole('button', { name: 'Arrêter', exact: true })).toBeDisabled();
    const sourceCard = page
      .locator('.source-status-card')
      .filter({ has: page.getByRole('heading', { name: 'Scraping fixture source', exact: true }) });
    await expect(
      sourceCard.getByRole('button', { name: 'Tester la source', exact: true }),
    ).toBeDisabled();
    await expect(sourceCard).toContainText('Non mesuré');
    await page.getByRole('radio', { name: 'Moins de 2 h', exact: true }).check();
    await page.getByRole('radio', { name: 'Moins de 2 h', exact: true }).focus();
    await page.keyboard.press('ArrowRight');
    await expect(page.getByRole('radio', { name: 'Moins de 6 h', exact: true })).toBeChecked();
    await page.getByRole('radio', { name: 'Moins de 2 h', exact: true }).check();
    await expect(page.locator('input[type=radio]:checked')).toHaveCount(1);
    await page
      .getByRole('button', { name: 'Enregistrer les critères du profil', exact: true })
      .click();
    await expect(page.locator('.success-note')).toHaveText('Profil enregistré');
    await page.reload();
    await expect(
      page.getByRole('combobox', { name: 'Profil à utiliser', exact: true }),
    ).toHaveValue(ids.profileId);
    await expect(page.getByRole('radio', { name: 'Moins de 2 h', exact: true })).toBeChecked();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: path.join(screenshots, 'scraping-desktop.png'), fullPage: true });
    await page
      .getByRole('link', { name: 'Rechercher dans mes offres importées', exact: true })
      .click();
    await page
      .getByRole('combobox', { name: 'Profil à utiliser', exact: true })
      .selectOption(ids.profileId);
    await page.getByRole('button', { name: 'Lancer la recherche locale', exact: true }).click();
    await expect(page.locator('.execution-panel .badge')).toHaveText('Terminée', {
      timeout: 20000,
    });
    await page.getByRole('link', { name: 'Scraping', exact: true }).click();
    await page
      .getByRole('combobox', { name: 'Profil à utiliser', exact: true })
      .selectOption(ids.profileId);
    await expect(page.locator('#scraping-history')).toContainText('Scraping fixture profile');
    await page.getByRole('link', { name: 'Voir les résultats locaux', exact: true }).click();
    await expect(page.locator('.result-row')).toHaveCount(1);
    await expect(page.locator('.result-row')).toContainText('Scraping fixture recent');
    await page.getByRole('link', { name: 'Scraping', exact: true }).click();
    await page
      .getByRole('combobox', { name: 'Profil à utiliser', exact: true })
      .selectOption(ids.profileId);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByRole('button', { name: 'Ouvrir la navigation', exact: true }).click();
    await page.getByRole('link', { name: 'Scraping', exact: true }).click();
    await expect(page.locator('.sidebar')).not.toBeInViewport();
    await expect(page.getByRole('heading', { name: 'Scraping', exact: true })).toBeVisible();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    ).toBe(true);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: path.join(screenshots, 'scraping-mobile.png') });
    await page.locator('#source-status').scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(screenshots, 'scraping-mobile-sources.png') });
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.getByRole('button', { name: 'EN', exact: true }).click();
    await expect(
      page.getByRole('heading', { name: 'No automatic collection configured', exact: true }),
    ).toBeVisible();
    await expect(page.getByRole('radio', { name: 'Less than 2 h', exact: true })).toBeChecked();
  } finally {
    // The harness always drops this disposable schema. Do not mask an original
    // assertion/locator error if the browser was closed after a timeout.
    if (!page.isClosed()) {
      await page
        .evaluate(async ({ sourceId, profileId }) => {
          await fetch(`/api/search/profiles/${profileId}`, { method: 'DELETE' });
          await fetch(`/api/sources/${sourceId}`, { method: 'DELETE' });
        }, ids)
        .catch(() => {});
    }
  }
});
