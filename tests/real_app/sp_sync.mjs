// The sync test's Super Productivity side (docs/dev-environment.md, sync
// test): sets up WebDAV sync in Super Productivity's own sync settings,
// creates and changes tasks through its UI, lets it sync, and saves its
// own export of the result and the task titles it shows, for
// check_sync.py.
//
//   node tests/real_app/sp_sync.mjs DIR ROUND
//
// ROUND 1 starts a fresh profile in DIR/profile, sets up sync and adds
// tasks; ROUND 2 reopens the profile and changes, completes, deletes and
// adds tasks. Each round syncs and writes DIR/roundN.sp.json (Super
// Productivity's "Export Data") and DIR/roundN.ui.json (titles of the open
// and done tasks it shows in Today). PENSUM_SP_URL picks the app (default:
// the live web app), PENSUM_DAV_URL the WebDAV server (default
// http://127.0.0.1:2345/, user and password "test"), PENSUM_DAV_FOLDER the
// folder on it (default super-productivity). PENSUM_SYNC_COMPRESS=1
// switches compression on, PENSUM_SYNC_PASSWORD sets encryption with that
// password at setup (#29), PENSUM_SYNC_SPLIT=1 switches on "Surgical sync"
// (the v3 split files, #30/#31). Logs counts only.
import { mkdirSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { join } from 'node:path';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const BASE = process.env.PENSUM_SP_URL ?? 'https://app.super-productivity.com/';
const DAV = process.env.PENSUM_DAV_URL ?? 'http://127.0.0.1:2345/';
const FOLDER = process.env.PENSUM_DAV_FOLDER ?? 'super-productivity';
const COMPRESS = process.env.PENSUM_SYNC_COMPRESS === '1';
const PASSWORD = process.env.PENSUM_SYNC_PASSWORD ?? '';
const SPLIT = process.env.PENSUM_SYNC_SPLIT === '1';
const local = /^http:\/\/(localhost|127\.0\.0\.1)[:/]/.test(BASE);
const [dir, round] = process.argv.slice(2);
if (!dir || !['1', '2'].includes(round)) {
  console.error('usage: node sp_sync.mjs DIR 1|2');
  process.exit(2);
}

// Test tasks; check_sync.py and the unit test fixture know these titles.
const T = {
  plants: 'Sync test: water the plants',
  letter: 'Sync test: write the letter',
  bike: 'Sync test: fix the bike',
  bikeRenamed: 'Sync test: fix the bike and the bell',
  bread: 'Sync test: bake bread',
  call: 'Sync test: call the plumber',
  sub: 'Sync test: buy flour',
};

mkdirSync(dir, { recursive: true });
const context = await chromium.launchPersistentContext(join(dir, 'profile'), {
  viewport: { width: 1200, height: 800 },
  acceptDownloads: true,
  ...(process.env.HTTPS_PROXY && !local
    ? { proxy: { server: process.env.HTTPS_PROXY, bypass: '127.0.0.1,localhost' } }
    : {}),
});
const page = context.pages()[0] ?? (await context.newPage());
const log = { syncs: [], errors: [] };
page.on('console', (message) => {
  const text = message.text();
  // Every completed upload (both formats); the v2 adapter also names its
  // syncVersion.
  const uploaded = text.match(/SyncWrapperService: Upload complete\. uploaded=(\d+)/);
  if (uploaded && Number(uploaded[1]) > 0) log.syncs.push(log.version ?? '?');
  const version = text.match(/Upload complete \(syncVersion=(\d+)/);
  if (version) log.version = Number(version[1]);
  if (/Sync complete, status=IN_SYNC/.test(text)) log.inSync = (log.inSync ?? 0) + 1;
  // Super Productivity marks expected misses itself, e.g. no previous
  // snapshot to back up on the first Surgical sync upload.
  if (/sync.*(error|failed)/i.test(text) && !/\(non-fatal\)/.test(text)) {
    log.errors.push(text.slice(0, 160));
  }
});

async function open() {
  for (let attempt = 1; ; attempt += 1) {
    try {
      await page.goto(`${BASE}#/tag/TODAY/tasks`, { waitUntil: 'networkidle', timeout: 90_000 });
      await page.locator('button.sync-btn').first().waitFor({ timeout: 30_000 });
      return;
    } catch (error) {
      if (attempt === 3) throw error;
      console.log(`app did not load, attempt ${attempt}`);
    }
  }
}

async function setupSync() {
  await page.locator('button.sync-btn').first().click();
  const signIn = page.locator('dialog-sync-setup');
  const cfg = page.locator('dialog-sync-cfg');
  await signIn.or(cfg).first().waitFor({ timeout: 15_000 });
  if (await signIn.isVisible()) await signIn.locator('.e2e-other-sync-options').click();
  await cfg.waitFor();
  await page.locator('formly-field-mat-select mat-select').first().click();
  await page.locator('mat-option').filter({ hasText: 'WebDAV' }).click();
  await page.locator('.e2e-baseUrl input').fill(DAV);
  await page.locator('.e2e-userName input').fill('test');
  await page.locator('.e2e-password input').fill('test');
  await page.locator('.e2e-syncFolderPath input').fill(FOLDER);
  if (COMPRESS || SPLIT) {
    const header = cfg.locator('formly-collapsible .collapsible-header', { hasText: 'Advanced' });
    if (!(await cfg.locator('formly-collapsible .collapsible-panel').isVisible())) await header.click();
    if (COMPRESS) await cfg.getByRole('checkbox', { name: /Enable compression/i }).setChecked(true);
    if (SPLIT) await cfg.getByRole('checkbox', { name: /Surgical sync/i }).setChecked(true);
  }
  await page.locator('mat-dialog-actions button[mat-flat-button]').click();
  await skipOrSetPassword();
  // The dialog sometimes ignores the first Save (Super Productivity's own
  // e2e tests retry the same way).
  const closed = await cfg.waitFor({ state: 'hidden', timeout: 8_000 }).then(() => true, () => false);
  if (!closed) {
    console.log('sync dialog still open, saving again');
    await page.locator('mat-dialog-actions button[mat-flat-button]').click();
    await skipOrSetPassword();
    await cfg.waitFor({ state: 'hidden', timeout: 15_000 });
  }
}

/** "Encrypt before first upload?": set the password, so the first upload
 *  is already encrypted, or skip. */
async function skipOrSetPassword() {
  if (PASSWORD) {
    const field = page.locator('.e2e-setup-encrypt-password');
    if (!(await field.waitFor({ timeout: 10_000 }).then(() => true, () => false))) return;
    await field.fill(PASSWORD);
    await page.locator('.e2e-setup-encrypt-confirm-password').click();
    await page.locator('.e2e-setup-encrypt-confirm-password').fill(PASSWORD);
    await page.locator('.e2e-setup-encrypt-submit').click();
  } else {
    const skip = page.locator('.e2e-setup-encrypt-skip');
    await skip.waitFor({ timeout: 10_000 }).then(() => skip.click()).catch(() => {});
  }
}

/** Click the sync button and wait until Super Productivity uploaded. */
async function sync() {
  const before = log.syncs.length;
  await closeAddBar();
  await page.locator('button.sync-btn').first().click();
  await page.waitForFunction(
    () => document.querySelector('button.sync-btn')?.getAttribute('data-sync-confirmation') === 'remote',
    null,
    { timeout: 30_000 },
  );
  const deadline = Date.now() + 30_000;
  while (log.syncs.length === before && Date.now() < deadline) await page.waitForTimeout(250);
  if (log.syncs.length === before) throw new Error('Super Productivity did not upload');
}

async function addTask(title) {
  const input = page.locator('add-task-bar.global .main-input');
  if (!(await input.isVisible())) await page.keyboard.press('Shift+A');
  await input.waitFor();
  await input.fill(title);
  await page.keyboard.press('Enter');
  await page.locator('task').filter({ hasText: title }).first().waitFor();
}

/** Close the add-task bar; its backdrop takes the clicks while open. */
async function closeAddBar() {
  const input = page.locator('add-task-bar.global .main-input');
  if (await input.isVisible()) {
    await page.keyboard.press('Escape');
    await input.waitFor({ state: 'hidden', timeout: 5_000 }).catch(() => {});
  }
  await page.locator('.backdrop').waitFor({ state: 'detached', timeout: 5_000 }).catch(() => {});
}

function task(title) {
  return page.locator('task').filter({ has: page.locator('task-title', { hasText: new RegExp(`^\\s*${title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*$`) }) }).first();
}

async function markDone(title) {
  await closeAddBar();
  const row = task(title);
  await row.hover();
  await row.locator('done-toggle').first().click();
  await page.waitForFunction(
    (id) => document.querySelector(`task[data-task-id="${id}"]`)?.classList.contains('isDone'),
    await row.getAttribute('data-task-id'),
    { timeout: 10_000 },
  );
}

async function rename(title, next) {
  await closeAddBar();
  const row = task(title);
  await row.locator('task-title').first().click();
  const area = row.locator('textarea').first();
  await area.waitFor();
  await area.fill(next);
  await page.keyboard.press('Tab');
  await task(next).waitFor();
}

async function addSubTask(title, sub) {
  await closeAddBar();
  const row = task(title);
  await row.focus();
  await row.press('a');
  const draft = page.locator('.e2e-add-subtask-input');
  await draft.waitFor();
  await draft.fill(sub);
  await page.keyboard.press('Enter');
  await page.keyboard.press('Escape');
  await draft.waitFor({ state: 'detached', timeout: 5_000 }).catch(() => {});
}

async function remove(title) {
  await closeAddBar();
  const row = task(title);
  // Super Productivity's shortcut for deleting the focused task.
  await row.focus();
  await row.press('Backspace');
  const confirm = page.locator('dialog-confirm button[mat-flat-button], dialog-confirm button[color=warn]');
  await confirm.first().click({ timeout: 3_000 }).catch(() => {});
  await task(title).waitFor({ state: 'detached', timeout: 10_000 });
}

async function shown() {
  const titles = async (selector) =>
    (await page.locator(`${selector} task-title`).allInnerTexts()).map((t) => t.trim());
  return { open: await titles('task:not(.isDone)'), done: await titles('task.isDone') };
}

async function exportData(out) {
  // The live app's CDN sometimes fails a script chunk; loading again helps.
  for (let attempt = 1; ; attempt += 1) {
    try {
      if (attempt === 1) await page.goto(`${BASE}#/config`, { waitUntil: 'networkidle' });
      else await page.reload({ waitUntil: 'networkidle' });
      await page.locator('[role=tab]').filter({ hasText: 'cloud_sync' }).click({ timeout: 30_000 });
      break;
    } catch (error) {
      if (attempt === 3) throw error;
      console.log(`settings did not load, attempt ${attempt}`);
    }
  }
  await page.getByText('Import/Export', { exact: true }).click();
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.locator('button').filter({ hasText: /^\s*file_upload\s*Export Data\s*$/ }).click(),
  ]);
  await download.saveAs(out);
}

try {
  await open();
  if (round === '1') {
    await setupSync();
    for (const title of [T.plants, T.letter, T.bike, T.bread]) await addTask(title);
    await markDone(T.letter);
    await addSubTask(T.bread, T.sub);
  } else {
    await rename(T.bike, T.bikeRenamed);
    await markDone(T.plants);
    await remove(T.bread);
    await addTask(T.call);
  }
  await sync();
  writeFileSync(join(dir, `round${round}.ui.json`), JSON.stringify(await shown()));
  await exportData(join(dir, `round${round}.sp.json`));
  console.log(
    `round ${round}: synced (syncVersion ${log.syncs.at(-1)}), ${log.syncs.length} uploads, ` +
      `${log.errors.length} sync errors logged`,
  );
  if (log.errors.length) {
    for (const line of log.errors) console.log(`sync error: ${line}`);
    process.exitCode = 1;
  }
} catch (error) {
  // What the app showed, for the failure artifact (test data only).
  await page.screenshot({ path: join(dir, `round${round}.error.png`) }).catch(() => {});
  throw error;
} finally {
  await context.close();
}
