import { test, expect } from '@playwright/test';
import { readFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';
const config = JSON.parse(readFileSync(process.env['JOBHUNTER_E2E_CONFIG']!, 'utf8')) as {
  email: string;
  password: string;
  cvFixturePath: string;
};
const screenshots = path.resolve('../../.cache/frontend-e2e/screenshots');
mkdirSync(screenshots, { recursive: true });

test('private CV original, reviewed candidate versions, activation and deletion', async ({
  page,
}) => {
  test.skip(process.platform !== 'win32', 'Native AppContainer parsing is verified on Windows CI.');
  test.setTimeout(120000);
  await page.goto('/auth/signin');
  await page.getByLabel('Adresse e-mail', { exact: true }).fill(config.email);
  await page.getByLabel('Mot de passe', { exact: true }).fill(config.password);
  await page.getByRole('button', { name: 'Se connecter', exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await page.getByRole('link', { name: 'Mes CV', exact: true }).click();
  const upload = page.getByTestId('cv-upload');
  await expect(upload).toBeEnabled();
  await upload.setInputFiles(config.cvFixturePath);
  await expect(page.getByRole('heading', { name: 'synthetic-cv.pdf', exact: true })).toBeVisible();
  await expect(page.getByTestId('cv-generate')).toBeEnabled();
  await page.getByTestId('cv-generate').click();
  await expect(page.getByRole('heading', { name: /Profil candidat/ })).toBeVisible();
  await expect(page.getByTestId('cv-activate')).toBeDisabled();
  await page
    .getByLabel('Titre professionnel', { exact: true })
    .fill('Synthetic developer <script>fixture</script>');
  await page.getByTestId('cv-save').click();
  await expect(page.getByRole('button', { name: /Révision 2/ })).toBeVisible();
  await expect(page.getByTestId('cv-validate')).toBeDisabled();
  await page
    .getByLabel('J’ai relu les faits, les corrections et les champs inconnus.', { exact: true })
    .check();
  await page.getByTestId('cv-validate').click();
  await expect(page.getByTestId('cv-activate')).toBeEnabled();
  await page.getByTestId('cv-activate').click();
  await expect(page.getByTestId('cv-activate')).toBeDisabled();
  await expect(page.locator('.candidate-card h2')).toContainText('Actif');
  const downloaded = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Télécharger l’original', exact: true }).click();
  const original = await downloaded;
  expect(readFileSync((await original.path())!)).toEqual(readFileSync(config.cvFixturePath));
  await original.delete();
  const exported = page.waitForEvent('download');
  await page
    .getByRole('button', { name: 'Exporter cette version et ses profils', exact: true })
    .click();
  const bundle = await exported;
  const json = JSON.parse(readFileSync((await bundle.path())!, 'utf8')) as {
    original_base64: string;
    candidate_profiles: unknown[];
  };
  expect(Buffer.from(json.original_base64, 'base64')).toEqual(readFileSync(config.cvFixturePath));
  expect(json.candidate_profiles.length).toBe(2);
  await bundle.delete();
  await page.reload();
  await expect(page.locator('.candidate-card h2')).toContainText('Actif');
  await page.screenshot({ path: path.join(screenshots, 'cv-desktop.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator('.sidebar')).not.toBeInViewport();
  await page.screenshot({ path: path.join(screenshots, 'cv-mobile.png'), fullPage: true });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
  ).toBeTruthy();
  // The native reviewed profile is reused for a real, local matching worker cycle.
  const matchingProfile = await page.evaluate(async () => {
    const source = '10000000-0000-4000-8000-000000000001';
    const imported = await fetch('/api/jobs/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_id: source,
        confirm: true,
        jobs: [
          {
            original_url: 'https://example.test/matching/synthetic',
            title: 'Matching synthetic developer',
            min_years: 0,
            mandatory_skills: ['Python', 'Rust'],
            description: 'Requirements\nPython required\nRust required',
          },
        ],
      }),
    });
    if (!imported.ok) throw new Error('Synthetic matching import failed');
    const profile = await fetch('/api/search/profiles', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'Matching synthetic preview',
        criteria: {
          source_ids: [source],
          include_keywords: ['Matching synthetic'],
          unknown_policy: 'exclude',
          experience_levels: [],
          publication_days: 0,
        },
      }),
    });
    if (!profile.ok) throw new Error('Synthetic matching profile failed');
    return (await profile.json()).id as string;
  });
  await page.goto('/search');
  await page.locator('#local-search-profile-choice').selectOption(matchingProfile);
  await page.getByRole('button', { name: 'Rechercher avec un aperçu CV', exact: true }).click();
  await expect(page.locator('.execution-panel .badge')).toHaveText('Terminée', { timeout: 20000 });
  const firstMatchingExecution = new URL(page.url()).searchParams.get('execution');
  expect(firstMatchingExecution).toBeTruthy();
  await page
    .getByRole('button', { name: 'Recalculer ces résultats sans collecte', exact: true })
    .click();
  await expect
    .poll(() => new URL(page.url()).searchParams.get('execution'))
    .not.toBe(firstMatchingExecution);
  await expect(page.locator('.execution-panel .badge')).toHaveText('Terminée', { timeout: 20000 });
  const execution = new URL(page.url()).searchParams.get('execution')!;
  const metadata = await (await page.request.get(`/api/search/executions/${execution}`)).json();
  expect(metadata.matching.cache_hits).toBe(1);
  expect(metadata.counts.scanned).toBe(0);
  await page.goto(`/results?execution=${execution}`);
  await expect(page.locator('.result-row')).toHaveCount(1);
  await page.getByRole('button', { name: 'Voir le détail', exact: true }).click();
  await expect(page.locator('jh-match-detail')).toContainText('Rust');
  await expect(page.locator('jh-match-detail')).toContainText('non calibré');
  await expect(page.locator('jh-match-detail')).toContainText('Non attesté');
  await page.screenshot({ path: path.join(screenshots, 'matching-mobile.png'), fullPage: true });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
  ).toBeTruthy();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({ path: path.join(screenshots, 'matching-desktop.png'), fullPage: true });
  await page.goto('/cvs');
  await page.getByRole('button', { name: 'Supprimer ce document', exact: true }).click();
  await page.getByTestId('cv-confirm-delete').click();
  await expect(page.getByText('Aucun CV enregistré.', { exact: false })).toBeVisible();
  const status = await page.evaluate(
    async () => (await fetch('/api/candidate-profiles/active')).status,
  );
  expect(status).toBe(409);
});

test('unsupported platform refuses CV parsing and keeps upload disabled', async ({ page }) => {
  test.skip(process.platform === 'win32', 'The native Windows parsing flow is tested separately.');
  await page.goto('/auth/signin');
  await page.getByLabel('Adresse e-mail', { exact: true }).fill(config.email);
  await page.getByLabel('Mot de passe', { exact: true }).fill(config.password);
  await page.getByRole('button', { name: 'Se connecter', exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await page.getByRole('link', { name: 'Mes CV', exact: true }).click();
  await expect(page.getByTestId('cv-upload')).toBeDisabled();
  await expect(page.getByRole('status')).toContainText('Analyse locale non configurée');
  const capabilities = await page.request.get('/api/cvs/capabilities');
  expect(capabilities.ok()).toBe(true);
  expect((await capabilities.json()).ready).toBe(false);
  const upload = await page.request.post('/api/cvs', {
    headers: {
      'Content-Type': 'application/pdf',
      'X-CV-Filename': 'synthetic-cv.pdf',
      Origin: new URL(page.url()).origin,
    },
    data: readFileSync(config.cvFixturePath),
  });
  expect(upload.status()).toBe(503);
  expect((await upload.json()).error.code).toBe('CV_SANDBOX_UNAVAILABLE');
});
