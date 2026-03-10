/**
 * Auth Setup — Obtains JWT via direct API call to backend
 * using TURNSTILE_TEST_SECRET to bypass Cloudflare Turnstile.
 *
 * Saves auth state to storageState files that other tests consume.
 *
 * Required env vars:
 *   TURNSTILE_TEST_SECRET — must match the backend's TURNSTILE_TEST_SECRET
 *   PLAYWRIGHT_BACKEND_URL (optional) — defaults to https://impuestify.com
 */
import { test as setup } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const BACKEND_URL = process.env.PLAYWRIGHT_BACKEND_URL || 'https://impuestify.com';
const FRONTEND_URL = process.env.PLAYWRIGHT_BASE_URL || 'https://impuestify.com';
const TURNSTILE_TEST_SECRET = process.env.TURNSTILE_TEST_SECRET || '';

const AUTH_DIR = path.join(__dirname, '.auth');

const USERS = {
    particular: { email: 'test.particular@impuestify.es', password: 'Test2026!' },
    autonomo: { email: 'test.autonomo@impuestify.es', password: 'Test2026!' },
};

async function getTokensViaAPI(email: string, password: string): Promise<{ access_token: string; refresh_token: string }> {
    const response = await fetch(`${BACKEND_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            email,
            password,
            turnstile_token: TURNSTILE_TEST_SECRET || undefined,
        }),
    });

    if (!response.ok) {
        const text = await response.text();
        throw new Error(`Login failed (${response.status}): ${text}`);
    }

    return response.json();
}

setup('authenticate as particular', async ({ page }) => {
    fs.mkdirSync(AUTH_DIR, { recursive: true });

    const tokens = await getTokensViaAPI(USERS.particular.email, USERS.particular.password);

    // Navigate to frontend and inject tokens into localStorage
    await page.goto(FRONTEND_URL, { waitUntil: 'domcontentloaded' });
    await page.evaluate((t) => {
        localStorage.setItem('access_token', t.access_token);
        localStorage.setItem('refresh_token', t.refresh_token);
    }, tokens);

    await page.context().storageState({ path: path.join(AUTH_DIR, 'particular.json') });
    console.log('Auth setup: particular OK');
});

setup('authenticate as autonomo', async ({ page }) => {
    fs.mkdirSync(AUTH_DIR, { recursive: true });

    const tokens = await getTokensViaAPI(USERS.autonomo.email, USERS.autonomo.password);

    await page.goto(FRONTEND_URL, { waitUntil: 'domcontentloaded' });
    await page.evaluate((t) => {
        localStorage.setItem('access_token', t.access_token);
        localStorage.setItem('refresh_token', t.refresh_token);
    }, tokens);

    await page.context().storageState({ path: path.join(AUTH_DIR, 'autonomo.json') });
    console.log('Auth setup: autonomo OK');
});
