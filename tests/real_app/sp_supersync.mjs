// SuperSync probe, Super Productivity's side (#34, docs/dev-environment.md,
// SuperSync probe): signs in to SuperSync in its own sync settings, with
// encryption password "test password", and syncs test tasks.
//
//   node tests/real_app/sp_supersync.mjs DIR 1|2
//
// Round 1 starts a fresh profile in DIR/profile, adds two tasks and sets up
// SuperSync (its first upload is a full-state op); round 2 adds a task and
// completes one (single ops). Only for the test account: the token is a
// network secret of the environment that the proxy puts into requests to
// sync.super-productivity.com, so the app gets a placeholder. Not in CI.
// Logs counts only.
import { createRequire } from 'node:module';
import { join } from 'node:path';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const BASE = 'https://app.super-productivity.com/';
const PASSWORD = 'test password';
const [dir, round] = process.argv.slice(2);
if (!dir || !['1', '2'].includes(round)) {
  console.error('usage: node sp_supersync.mjs DIR 1|2');
  process.exit(2);
}

const context = await chromium.launchPersistentContext(join(dir, 'profile'), {
  viewport: { width: 1200, height: 800 },
  proxy: { server: process.env.HTTPS_PROXY, bypass: '127.0.0.1,localhost' },
});
const page = context.pages()[0] ?? (await context.newPage());
const uploads = [];
page.on('console', (message) => {
  const done = message.text().match(/Upload complete\. uploaded=(\d+)/);
  if (done) uploads.push(Number(done[1]));
});

async function addTask(title) {
  const input = page.locator('add-task-bar.global .main-input');
  if (!(await input.isVisible())) await page.keyboard.press('Shift+A');
  await input.fill(title);
  await page.keyboard.press('Enter');
  await page.locator('task').filter({ hasText: title }).first().waitFor();
  await page.keyboard.press('Escape');
  await page.locator('.backdrop').waitFor({ state: 'detached', timeout: 5_000 }).catch(() => {});
}

async function setupSuperSync() {
  await page.locator('button.sync-btn').first().click({ button: 'right' });
  const cfg = page.locator('dialog-sync-cfg');
  const signIn = page.locator('dialog-sync-setup');
  await signIn.or(cfg).first().waitFor({ timeout: 15_000 });
  if (await signIn.isVisible()) await signIn.locator('.e2e-other-sync-options').click();
  await cfg.waitFor();
  await page.locator('formly-field-mat-select mat-select').first().click();
  await page.locator('mat-option').filter({ hasText: 'SuperSync' }).click();
  const token = page.locator('.e2e-accessToken input, .e2e-accessToken textarea').first();
  if (!(await token.isVisible())) {
    await cfg.locator('formly-collapsible .collapsible-header', { hasText: /Advanced/ }).first().click();
  }
  await token.fill('proxy-injected');
  await page.locator('mat-dialog-actions button[mat-flat-button]').click();
  // SuperSync requires encryption: its dialog asks for the password.
  const enc = page.locator('dialog-enable-encryption');
  await enc.waitFor({ timeout: 20_000 });
  await enc.locator('input[type="password"]').first().fill(PASSWORD);
  await enc.locator('input[type="password"]').nth(1).fill(PASSWORD);
  await enc.locator('button[mat-flat-button]').click();
}

try {
  await page.goto(`${BASE}#/tag/TODAY/tasks`, { waitUntil: 'networkidle', timeout: 90_000 });
  if (round === '1') {
    await addTask('SuperSync test: water the plants');
    await addTask('SuperSync test: write the letter');
    await setupSuperSync();
  } else {
    await addTask('SuperSync test: fix the bike');
    const row = page.locator('task').filter({ hasText: 'write the letter' }).first();
    await row.hover();
    await row.locator('done-toggle').first().click();
    await page.waitForTimeout(1_000);
    await page.locator('button.sync-btn').first().click();
  }
  await page.waitForTimeout(12_000);
  console.log(`round ${round}: ${uploads.length} syncs, ${uploads.reduce((a, b) => a + b, 0)} ops uploaded`);
} finally {
  await context.close();
}
