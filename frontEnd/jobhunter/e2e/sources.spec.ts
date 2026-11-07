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
  await page.getByRole('link', { name: 'Sources', exact: true }).click();
  await expect(page.locator('.source-card')).toHaveCount(4);
}
test('Tunisian sources: saved selection, encoded link, custom source and mobile layout', async ({
  page,
}) => {
  await signIn(page);
  await page.getByRole('button', { name: 'Sites tunisiens', exact: true }).click();
  await expect(page.locator('.source-card')).toHaveCount(2);
  const card = page.locator('[data-source=keejob]');
  await card.getByRole('checkbox').click();
  await expect(card.getByRole('checkbox')).toBeChecked();
  await card.getByLabel('Mots-clés').fill('Python & SQL');
  await card.getByLabel('Lieu', { exact: true }).fill('Tunis');
  await card.getByRole('button', { name: 'Enregistrer et préparer le lien' }).click();
  const search = card.getByRole('link', { name: 'Ouvrir la recherche' });
  await expect(search).toHaveAttribute('href', /keywords=Python\+%26\+SQL\+Tunis/);
  await page.reload();
  await expect(card.getByRole('checkbox')).toBeChecked();
  await expect(card.getByLabel('Mots-clés')).toHaveValue('Python & SQL');
  await page.getByLabel('Nom du site', { exact: true }).fill('Fixture Tunisie');
  await page.getByLabel('Adresse HTTPS du site').fill('https://example.test');
  await page.getByRole('button', { name: 'Ajouter un site', exact: true }).click();
  const custom = page
    .locator('.source-card')
    .filter({ has: page.getByRole('heading', { name: 'Fixture Tunisie' }) });
  await expect(custom).toBeVisible();
  await custom.getByRole('button', { name: 'Retirer ce site' }).click();
  await expect(custom).toHaveCount(0);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: path.join(screenshots, 'sources-desktop.png') });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('heading', { name: 'Sources', exact: true })).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
  ).toBeTruthy();
  await expect
    .poll(async () => (await page.locator('.sidebar').boundingBox())!.x)
    .toBeLessThanOrEqual(-249);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: path.join(screenshots, 'sources-mobile.png') });
});
test('confirmed imports: preview, idempotence, preserved first discovery and CSV row errors', async ({
  page,
}) => {
  await signIn(page);
  await page.getByLabel('Source de l’offre').selectOption({ label: 'Tanitjobs' });
  await page
    .getByLabel('Lien HTTPS de l’offre')
    .fill('https://example.test/fixture-import?utm_source=one');
  await page.getByLabel('Intitulé (facultatif)').fill('Synthetic Python role');
  await page
    .getByLabel('Description (facultative)')
    .fill('<script>fixture</script> Plain pasted text');
  await page.getByRole('button', { name: 'Vérifier avant import', exact: true }).click();
  await expect(page.locator('.preview-card')).toContainText('<script>fixture</script>');
  await expect(page.locator('.imported-job')).toHaveCount(0);
  await page.getByRole('button', { name: 'Confirmer l’import', exact: true }).click();
  await expect(page.locator('.import-success')).toContainText('Nouvelles offres : 1');
  await expect(page.locator('.imported-job')).toHaveCount(1);
  const discovery = await page.locator('.imported-job dd').first().textContent();
  await page
    .getByLabel('Lien HTTPS de l’offre')
    .fill('https://example.test/fixture-import?utm_source=two');
  await page.getByRole('button', { name: 'Vérifier avant import', exact: true }).click();
  await page.getByRole('button', { name: 'Confirmer l’import', exact: true }).click();
  await expect(page.locator('.import-success')).toContainText('Offres déjà présentes : 1');
  await expect(page.locator('.imported-job')).toHaveCount(1);
  expect(await page.locator('.imported-job dd').first().textContent()).toBe(discovery);
  await page.getByLabel('Fichier CSV', { exact: true }).setInputFiles({
    name: 'fixture.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from(
      'url,title\nhttps://example.test/csv,CSV fixture\njavascript:bad,Invalid\n',
    ),
  });
  await page.getByRole('button', { name: 'Vérifier le CSV', exact: true }).click();
  await expect(page.locator('.preview-card')).toContainText('Lignes à corriger : 1');
  await expect(
    page.getByRole('button', { name: 'Confirmer l’import', exact: true }),
  ).toBeDisabled();
  await page.getByLabel('Fichier CSV', { exact: true }).setInputFiles({
    name: 'fixture.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from(
      'url;title;visa_status;visa_evidence;published_at\nhttps://example.test/csv;CSV fixture;CONFIRMED;Synthetic visa evidence;2026-11-07T12:00:00+00:00\n',
    ),
  });
  await page.getByRole('button', { name: 'Vérifier le CSV', exact: true }).click();
  await expect(page.locator('.preview-card')).toContainText('Lignes à corriger : 0');
  await expect(page.locator('.preview-card')).toContainText('Synthetic visa evidence');
  await expect(page.locator('.preview-card')).toContainText('2026-11-07T12:00:00');
  await page.getByRole('button', { name: 'Confirmer l’import', exact: true }).click();
  await expect(page.locator('.imported-job')).toHaveCount(2);
  await page.screenshot({ path: path.join(screenshots, 'sources-imported.png'), fullPage: true });
});
