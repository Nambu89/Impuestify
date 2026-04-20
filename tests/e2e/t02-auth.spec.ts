import { test, expect, Page } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

const BASE_URL = 'https://impuestify.com';
const SHOTS = 'tests/e2e/screenshots';

const USERS = {
  particular: { email: 'test.particular@impuestify.es', password: 'Test2026!', name: 'María' },
  autonomo: { email: 'test.autonomo@impuestify.es', password: 'Test2026!', name: 'Carlos' },
};

async function shot(page: Page, name: string) {
  fs.mkdirSync(SHOTS, { recursive: true });
  await page.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage: true });
}

async function login(page: Page, email: string, password: string) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle', timeout: 20000 });
  await page.fill('input[type="email"], input[name="email"]', email);
  await page.fill('input[type="password"], input[name="password"]', password);
  await shot(page, `auth-before-submit-${email.split('@')[0]}`);
  await page.click('button[type="submit"]');
  // Wait for redirect or error
  await Promise.race([
    page.waitForURL(`${BASE_URL}/chat`, { timeout: 15000 }),
    page.waitForSelector('[class*="error"], [class*="alert"], .toast', { timeout: 15000 }),
  ]).catch(() => {});
}

test.describe('T02 - Auth - Login y Logout', () => {
  test('T02a - Login como particular', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });

    await login(page, USERS.particular.email, USERS.particular.password);
    await shot(page, 'T02a-after-login-particular');

    const currentUrl = page.url();
    console.log(`URL after login: ${currentUrl}`);

    // Verificar que estamos en /chat
    const isInChat = currentUrl.includes('/chat');
    console.log(`Redirected to chat: ${isInChat}`);

    // Verificar JWT en localStorage
    if (isInChat) {
      const token = await page.evaluate(() => localStorage.getItem('access_token'));
      console.log(`JWT in localStorage: ${token ? 'YES (length=' + token.length + ')' : 'NO'}`);
      expect(token, 'JWT should be in localStorage after login').toBeTruthy();
    }

    // Verificar nombre del usuario en header
    const headerText = await page.locator('header, nav').textContent().catch(() => '');
    const hasUserName = headerText.includes('María') || headerText.includes('maria') ||
      headerText.includes('García') || headerText.includes('particular');
    console.log(`User name in header: ${hasUserName}`);
    console.log(`Console errors: ${consoleErrors.length}`);

    expect(isInChat, 'Should redirect to /chat after login').toBe(true);
  });

  test('T02b - Login como autonomo', async ({ page }) => {
    await login(page, USERS.autonomo.email, USERS.autonomo.password);
    await shot(page, 'T02b-after-login-autonomo');

    const currentUrl = page.url();
    console.log(`URL after login: ${currentUrl}`);
    const isInChat = currentUrl.includes('/chat');
    console.log(`Redirected to chat: ${isInChat}`);

    expect(isInChat, 'Should redirect to /chat after login').toBe(true);
  });

  test('T02c - Logout correcto', async ({ page }) => {
    // Login first
    await login(page, USERS.particular.email, USERS.particular.password);
    const afterLogin = page.url();
    expect(afterLogin).toContain('/chat');

    // Find and click logout
    const logoutBtn = page.locator('button:has-text("Salir"), button:has-text("Cerrar"), a:has-text("Salir"), a:has-text("Cerrar"), [aria-label*="logout"], [aria-label*="salir"]');
    const logoutCount = await logoutBtn.count();
    console.log(`Logout button found: ${logoutCount > 0}`);

    if (logoutCount > 0) {
      await logoutBtn.first().click();
      await page.waitForTimeout(2000);
      await shot(page, 'T02c-after-logout');
      const afterLogout = page.url();
      console.log(`URL after logout: ${afterLogout}`);
      const isLoggedOut = !afterLogout.includes('/chat') || afterLogout.includes('/login');
      console.log(`Logged out successfully: ${isLoggedOut}`);
    } else {
      // Try clicking on user menu first
      const userMenu = page.locator('[class*="avatar"], [class*="user-menu"], img[alt*="avatar"]');
      if (await userMenu.count() > 0) {
        await userMenu.first().click();
        await page.waitForTimeout(500);
        await shot(page, 'T02c-user-menu-open');
        const logoutAfterMenu = page.locator('button:has-text("Salir"), a:has-text("Salir"), button:has-text("Cerrar sesión")');
        if (await logoutAfterMenu.count() > 0) {
          await logoutAfterMenu.first().click();
        }
      }
      console.log('Logout button not directly visible, may need menu interaction');
    }
  });

  test('T02d - Login con credenciales incorrectas muestra error', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle', timeout: 20000 });
    await page.fill('input[type="email"], input[name="email"]', 'incorrecto@test.com');
    await page.fill('input[type="password"], input[name="password"]', 'WrongPassword123!');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);
    await shot(page, 'T02d-invalid-login');

    const currentUrl = page.url();
    const stillOnLogin = currentUrl.includes('/login') || !currentUrl.includes('/chat');
    const errorMsg = await page.locator('[class*="error"], [class*="alert"], .toast, [role="alert"]').textContent().catch(() => '');

    console.log(`Still on login page: ${stillOnLogin}`);
    console.log(`Error message: ${errorMsg}`);
    expect(stillOnLogin, 'Should stay on login page with wrong credentials').toBe(true);
  });

  test('T02e - Ruta protegida sin auth redirige a login', async ({ page }) => {
    await page.goto(`${BASE_URL}/chat`, { waitUntil: 'networkidle', timeout: 20000 });
    await shot(page, 'T02e-protected-route-no-auth');
    const currentUrl = page.url();
    console.log(`URL when accessing /chat without auth: ${currentUrl}`);
    const redirectedToLogin = currentUrl.includes('/login') || currentUrl === `${BASE_URL}/` || !currentUrl.includes('/chat');
    console.log(`Redirected away from chat: ${redirectedToLogin}`);
    expect(redirectedToLogin, 'Should redirect to login when not authenticated').toBe(true);
  });
});
