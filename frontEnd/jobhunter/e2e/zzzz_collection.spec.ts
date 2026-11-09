import { test, expect } from '@playwright/test';
import { readFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';
const config = JSON.parse(readFileSync(process.env['JOBHUNTER_E2E_CONFIG']!, 'utf8')) as {
  email: string;
  password: string;
};

test('simulated collection API: saved profile, limits, existing SSE progress, reload and cancel', async ({
  page,
}) => {
  page.setDefaultTimeout(10000);
  await page.goto('/auth/signin');
  await page.getByLabel('Adresse e-mail', { exact: true }).fill(config.email);
  await page.getByLabel('Mot de passe', { exact: true }).fill(config.password);
  await page.getByRole('button', { name: 'Se connecter', exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  const profile = {
    id: 'synthetic-collection-profile',
    name: 'Synthetic collection only',
    description: '',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    criteria: {
      source_ids: ['synthetic-source'],
      domains: [],
      titles: [],
      include_keywords: [],
      exclude_keywords: [],
      countries: [],
      cities: [],
      work_modes: [],
      experience_levels: [],
      max_years: 3,
      visa_statuses: [],
      publication_days: 0,
      publication_minutes: 1440,
      novelty: 'all',
      unknown_policy: 'include',
      mode: 'MANUAL',
      linked_cv_id: null,
      min_score: 0,
      notifications_enabled: false,
    },
  };
  const execution = {
    id: 'synthetic-run',
    profile_id: profile.id,
    profile_name: profile.name,
    scope: 'COLLECTED_OFFERS',
    status: 'RUNNING',
    criteria: profile.criteria,
    cancel_requested: false,
    created_at: profile.created_at,
    started_at: profile.created_at,
    finished_at: null,
    counts: { collected: 2, created: 2, results: 2 },
    reason: null,
    stage: 'COLLECT',
    cursor: 0,
    attempt: 1,
    heartbeat_at: null,
    sources: [
      {
        source_id: 'synthetic-source',
        source_name: 'Synthetic permitted fixture',
        status: 'SUCCEEDED',
        reason: 'READY',
      },
    ],
  };
  let created = false;
  let startBody: unknown;
  let cancelled = false;
  // Browser-only API simulation. No provider or collector endpoint is contacted.
  await page.route('**/api/sources', (route) =>
    route.fulfill({
      json: [
        {
          id: 'synthetic-source',
          name: 'Synthetic permitted fixture',
          manual_import_supported: false,
          enabled: true,
          integration_type: 'API',
          legal_status: 'PERMITTED',
          jobs_collected: null,
          last_successful_sync: null,
        },
      ],
    }),
  );
  await page.route('**/api/sources/synthetic-source/collection', (route) =>
    route.fulfill({
      json: {
        source_id: 'synthetic-source',
        name: 'Synthetic permitted fixture',
        eligible: true,
        reason: 'READY',
        limits: { max_results: 10 },
      },
    }),
  );
  await page.route('**/api/search/profiles', (route) => route.fulfill({ json: [profile] }));
  await page.route('**/api/search/executions', async (route) => {
    if (route.request().method() === 'POST') {
      created = true;
      startBody = route.request().postDataJSON();
      await route.fulfill({ status: 202, json: execution });
    } else await route.fulfill({ json: created ? [execution] : [] });
  });
  await page.route('**/api/search/executions/synthetic-run', (route) =>
    route.fulfill({ json: execution }),
  );
  await page.route('**/api/search/executions/synthetic-run/events', async (route) => {
    execution.status = 'SUCCEEDED';
    execution.stage = 'FILTER';
    await route.fulfill({
      contentType: 'text/event-stream',
      body: `event: progress\ndata: ${JSON.stringify(execution)}\n\n`,
    });
  });
  await page.route('**/api/search/executions/synthetic-run/cancel', async (route) => {
    cancelled = true;
    execution.status = 'CANCELLED';
    execution.cancel_requested = true;
    await route.fulfill({ json: execution });
  });
  await page.goto('/scraping');
  await expect(
    page.getByRole('button', { name: 'Lancer la recherche', exact: true }),
  ).toBeEnabled();
  await page.getByRole('spinbutton', { name: 'Nombre maximal', exact: false }).fill('7');
  await page.getByRole('button', { name: 'Lancer la recherche', exact: true }).click();
  await expect(page).toHaveURL(/\/search\?execution=synthetic-run$/);
  await expect(page.locator('.execution-panel')).toContainText('Collecte puis filtrage');
  await expect(page.locator('.execution-panel')).toContainText('Termin');
  expect(startBody).toEqual({ profile_id: profile.id, scope: 'COLLECTED_OFFERS', max_results: 7 });
  execution.status = 'RUNNING';
  await page.goto('/scraping');
  await page.reload();
  await expect(page.getByRole('button', { name: 'Arrêter', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Arrêter', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Arrêter', exact: true })).toBeDisabled();
  expect(cancelled).toBe(true);
  await expect(page.locator('#scraping-history')).toContainText('Collecte puis filtrage');
  const folder = path.resolve('../../.cache/frontend-e2e/screenshots');
  mkdirSync(folder, { recursive: true });
  await page.screenshot({
    path: path.join(folder, 'collection-simulated-desktop.png'),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator('.sidebar')).not.toBeInViewport();
  await expect(page.getByRole('heading', { name: 'Scraping', exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: path.join(folder, 'collection-simulated-mobile.png') });
});
