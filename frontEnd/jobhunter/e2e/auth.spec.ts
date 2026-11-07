import { test, expect, Page } from '@playwright/test';
import { readFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';

const config = JSON.parse(readFileSync(process.env['JOBHUNTER_E2E_CONFIG']!, 'utf8')) as {
  email: string;
  password: string;
  baseURL: string;
};
const screenshots = path.resolve('../../.cache/frontend-e2e/screenshots');
mkdirSync(screenshots, { recursive: true });

async function signIn(page: Page): Promise<void> {
  await page.goto('/auth/signin', { waitUntil: 'domcontentloaded' });
  await page.getByLabel('Adresse e-mail', { exact: true }).fill(config.email);
  await page.getByLabel('Mot de passe', { exact: true }).fill(config.password);
  await page.getByRole('button', { name: 'Se connecter', exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

test('protected account, real login, language persistence and logout', async ({
  page,
  context,
}) => {
  await page.goto('/account', { waitUntil: 'domcontentloaded' });
  await expect(page).toHaveURL(/\/auth\/signin/);
  await expect(page.locator('.auth-card')).toHaveCSS('display', 'grid');
  await page.screenshot({ path: path.join(screenshots, 'signin-desktop.png'), fullPage: true });
  await page.getByLabel('Adresse e-mail', { exact: true }).fill(config.email);
  await page.getByLabel('Mot de passe', { exact: true }).fill(config.password);
  await page.getByRole('button', { name: 'Se connecter', exact: true }).click();
  await expect(page).toHaveURL(/\/account$/);
  await expect(page.getByRole('heading', { name: config.email })).toBeVisible();
  const cookieFlags = (await context.cookies())
    .filter((cookie) => cookie.name.startsWith('__Host-jh_'))
    .map((cookie) => ({
      httpOnly: cookie.httpOnly,
      secure: cookie.secure,
      sameSite: cookie.sameSite,
    }));
  expect(cookieFlags).toHaveLength(2);
  expect(
    cookieFlags.every((flags) => flags.httpOnly && flags.secure && flags.sameSite === 'Strict'),
  ).toBeTruthy();
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([]);
  await page.getByRole('button', { name: 'EN', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Your personal account' })).toBeVisible();
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page.getByRole('heading', { name: 'Your personal account' })).toBeVisible();
  await page.screenshot({ path: path.join(screenshots, 'account-desktop.png'), fullPage: true });
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page).toHaveURL(/\/auth\/signin/);
  await expect(page).not.toHaveURL(/reason=expired/);
  await page.goto('/account', { waitUntil: 'domcontentloaded' });
  await expect(page).toHaveURL(/\/auth\/signin/);
});

test('expired access cookie is renewed through the real rotating refresh cookie', async ({
  page,
  context,
}) => {
  await signIn(page);
  await page.screenshot({ path: path.join(screenshots, 'dashboard-desktop.png'), fullPage: true });
  await context.clearCookies({ name: '__Host-jh_access' });
  const renewal = page.waitForResponse(
    (response) => response.url().endsWith('/api/auth/refresh') && response.status() === 200,
  );
  await page.reload({ waitUntil: 'domcontentloaded' });
  await renewal;
  await expect(page.getByRole('heading', { name: 'Bienvenue dans votre espace' })).toBeVisible();
});

test('mobile layout, keyboard drawer and account navigation', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/auth/signin', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('.auth-card')).toHaveCSS('display', 'block');
  await page.screenshot({ path: path.join(screenshots, 'signin-mobile.png'), fullPage: true });
  await signIn(page);
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
  ).toBeTruthy();
  await page.screenshot({ path: path.join(screenshots, 'dashboard-mobile.png'), fullPage: true });
  const toggle = page.getByRole('button', { name: 'Ouvrir la navigation' });
  await toggle.click();
  await expect(toggle).toHaveAttribute('aria-expanded', 'true');
  await page.keyboard.press('Shift+Tab');
  await expect(page.locator('aside a').last()).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(toggle).toBeFocused();
  await toggle.click();
  await page.locator('aside').getByRole('link', { name: 'Mon compte', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Votre compte personnel' })).toBeVisible();
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
  ).toBeTruthy();
});

test('lost refresh cookie redirects an open account to an expired-session sign-in', async ({
  page,
  context,
}) => {
  await signIn(page);
  await context.clearCookies();
  await page.locator('aside').getByRole('link', { name: 'Mon compte', exact: true }).click();
  await expect(page).toHaveURL(/\/auth\/signin.*reason=expired/);
  await expect(page.getByRole('status')).toContainText('Votre session a expiré');
});

test('unavailable API has a visible error rather than an authenticated empty workspace', async ({
  page,
}) => {
  await page.route('**/api/**', (route) =>
    route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: '{"error":{"code":"UNAVAILABLE"}}',
    }),
  );
  await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
  await expect(page).toHaveURL(/\/auth\/signin/);
  await expect(page.getByRole('status')).toContainText('Le service est indisponible');
  await expect(page.locator('.sidebar')).toHaveCount(0);
});
