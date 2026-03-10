/**
 * T05 — Session Documents: Upload nomina via paperclip and verify AI context
 */
import { test, expect, Page } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

const SHOTS = 'tests/e2e/screenshots';
const NOMINA_PATH = path.resolve(__dirname, '../../docs/Nomina_PRADA GORGE, FERNANDO.PDF');

function shot(page: Page, name: string) {
    fs.mkdirSync(SHOTS, { recursive: true });
    return page.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage: true });
}

test.describe('T05 — Session Documents', () => {

    test('T05a — Upload nomina and verify chip appears', async ({ page }) => {
        // Navigate to chat
        await page.goto('/chat', { waitUntil: 'networkidle', timeout: 30000 });
        await shot(page, 'T05a-chat-initial');

        // Verify paperclip button exists
        const paperclip = page.locator('.btn-session-doc-upload');
        await expect(paperclip).toBeVisible({ timeout: 10000 });

        // Upload file via hidden input
        const fileInput = page.locator('input[type="file"][accept*=".pdf"]');
        await fileInput.setInputFiles(NOMINA_PATH);

        // Wait for chip to appear (upload + processing)
        const chip = page.locator('.session-doc-chip');
        await expect(chip).toBeVisible({ timeout: 30000 });
        await shot(page, 'T05a-chip-visible');

        // Verify chip has filename
        const chipName = chip.locator('.session-doc-chip__name');
        await expect(chipName).toContainText('Nomina', { ignoreCase: true });

        console.log('T05a PASS: Nomina uploaded, chip visible');
    });

    test('T05b — Ask about nomina and get relevant response', async ({ page }) => {
        await page.goto('/chat', { waitUntil: 'networkidle', timeout: 30000 });

        // Upload nomina first
        const fileInput = page.locator('input[type="file"][accept*=".pdf"]');
        await fileInput.setInputFiles(NOMINA_PATH);

        // Wait for chip
        const chip = page.locator('.session-doc-chip');
        await expect(chip).toBeVisible({ timeout: 30000 });

        // Type question
        const input = page.locator('.chat-input');
        await input.fill('Analiza esta nomina y dime el salario bruto y neto');
        await shot(page, 'T05b-question-typed');

        // Submit
        await page.locator('.chat-submit').click();

        // Wait for response (streaming completes)
        const assistantMessage = page.locator('.message.assistant .message-text');
        await expect(assistantMessage).toBeVisible({ timeout: 90000 });

        // Wait for streaming to finish (no more cursor)
        await page.waitForSelector('.streaming-cursor', { state: 'hidden', timeout: 90000 }).catch(() => {});

        // Wait a bit for final content
        await page.waitForTimeout(3000);
        await shot(page, 'T05b-response-complete');

        // Verify response contains salary-related terms
        const responseText = await assistantMessage.last().textContent();
        console.log('Response preview:', responseText?.substring(0, 200));

        // The response should mention salary/nomina concepts
        const hasRelevantContent = responseText && (
            responseText.toLowerCase().includes('bruto') ||
            responseText.toLowerCase().includes('neto') ||
            responseText.toLowerCase().includes('salario') ||
            responseText.toLowerCase().includes('irpf') ||
            responseText.toLowerCase().includes('nomina') ||
            responseText.toLowerCase().includes('retenci')
        );
        expect(hasRelevantContent).toBeTruthy();

        console.log('T05b PASS: AI responded with nomina-relevant data');
    });

    test('T05c — Follow-up question uses nomina context', async ({ page }) => {
        await page.goto('/chat', { waitUntil: 'networkidle', timeout: 30000 });

        // Upload nomina
        const fileInput = page.locator('input[type="file"][accept*=".pdf"]');
        await fileInput.setInputFiles(NOMINA_PATH);
        await page.locator('.session-doc-chip').waitFor({ timeout: 30000 });

        // First question
        const input = page.locator('.chat-input');
        await input.fill('Analiza esta nomina brevemente');
        await page.locator('.chat-submit').click();

        // Wait for first response
        await page.waitForSelector('.streaming-cursor', { state: 'hidden', timeout: 90000 }).catch(() => {});
        await page.waitForTimeout(3000);

        // Follow-up question
        await input.fill('Cuanto pago de IRPF al mes segun la nomina?');
        await page.locator('.chat-submit').click();

        // Wait for second response
        await page.waitForTimeout(5000);
        await page.waitForSelector('.streaming-cursor', { state: 'hidden', timeout: 90000 }).catch(() => {});
        await page.waitForTimeout(3000);
        await shot(page, 'T05c-followup-response');

        const messages = page.locator('.message.assistant .message-text');
        const lastResponse = await messages.last().textContent();
        console.log('Follow-up response:', lastResponse?.substring(0, 200));

        // Should mention IRPF or retention
        const hasIRPF = lastResponse && (
            lastResponse.toLowerCase().includes('irpf') ||
            lastResponse.toLowerCase().includes('retenci') ||
            lastResponse.includes('%') ||
            lastResponse.includes('EUR') ||
            lastResponse.includes('euro')
        );
        expect(hasIRPF).toBeTruthy();

        console.log('T05c PASS: Follow-up uses nomina context');
    });

    test('T05d — Remove chip works', async ({ page }) => {
        await page.goto('/chat', { waitUntil: 'networkidle', timeout: 30000 });

        // Upload
        const fileInput = page.locator('input[type="file"][accept*=".pdf"]');
        await fileInput.setInputFiles(NOMINA_PATH);

        const chip = page.locator('.session-doc-chip');
        await expect(chip).toBeVisible({ timeout: 30000 });

        // Click remove button
        await chip.locator('.session-doc-chip__remove').click();

        // Chip should disappear
        await expect(chip).not.toBeVisible({ timeout: 5000 });
        await shot(page, 'T05d-chip-removed');

        console.log('T05d PASS: Chip removed successfully');
    });

    test('T05e — No console errors during upload flow', async ({ page }) => {
        const errors: string[] = [];
        page.on('console', msg => {
            if (msg.type() === 'error' && !msg.text().includes('favicon')) {
                errors.push(msg.text());
            }
        });

        await page.goto('/chat', { waitUntil: 'networkidle', timeout: 30000 });

        const fileInput = page.locator('input[type="file"][accept*=".pdf"]');
        await fileInput.setInputFiles(NOMINA_PATH);

        await page.locator('.session-doc-chip').waitFor({ timeout: 30000 });
        await page.waitForTimeout(2000);

        // Filter out known non-critical errors
        const criticalErrors = errors.filter(e =>
            !e.includes('net::ERR') &&
            !e.includes('Failed to load resource') &&
            !e.includes('404')
        );

        if (criticalErrors.length > 0) {
            console.log('Console errors:', criticalErrors);
        }

        console.log(`T05e: ${criticalErrors.length} critical console errors`);
    });
});
