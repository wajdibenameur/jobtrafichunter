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
  test.setTimeout(60000);
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
  await page.getByRole('button', { name: 'Supprimer ce document', exact: true }).click();
  await page.getByTestId('cv-confirm-delete').click();
  await expect(page.getByText('Aucun CV enregistré.', { exact: false })).toBeVisible();
  const status = await page.evaluate(
    async () => (await fetch('/api/candidate-profiles/active')).status,
  );
  expect(status).toBe(409);
});
