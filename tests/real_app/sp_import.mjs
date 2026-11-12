// Imports Pensum's exports into a real Super Productivity through its own
// "Import from File" in Settings → Sync & Backup, each in a fresh browser
// profile, checks that it took the file without a repair, and saves
// Super Productivity's own export of the result for check_round_trip.py
// (docs/dev-environment.md, real app).
//
//   node tests/real_app/sp_import.mjs DIR NAME...
//
// For each NAME it reads DIR/NAME.json and DIR/NAME.expect.json (from
// make_exports.py) and writes DIR/NAME.sp.json. A file fails when Super
// Productivity opens a dialog, or logs a validation failure or a repair
// that the same import of its own fixture (DIR/baseline.json, when
// expect.baseline names it) does not log too; and when a project title
// Pensum wrote is missing from the menu.
//
// PENSUM_SP_URL picks the app: by default the live web app; CI runs
// Super Productivity's Docker image pinned in tests/real_app/Dockerfile
// on localhost. The live app goes through HTTPS_PROXY when it is set.
// Logs name ids and counts only. Uses the Playwright of the environment.
import { readFileSync, existsSync } from 'node:fs';
import { createRequire } from 'node:module';
import { join } from 'node:path';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const BASE = process.env.PENSUM_SP_URL ?? 'https://app.super-productivity.com/';
const local = /^http:\/\/(localhost|127\.0\.0\.1)[:/]/.test(BASE);
const [dir, ...names] = process.argv.slice(2);
if (!dir || names.length === 0) {
  console.error('usage: node sp_import.mjs DIR NAME...');
  process.exit(2);
}

// Super Productivity's log lines that mean it found the data invalid or
// changed it while importing (BackupService, data-repair, typia auto-fix).
const REPAIR = /validation failed|attempting repair|auto-fix|repair|orphan|missing|restored/i;
// Lines that only report that nothing was found.
const NOTHING = /count: 0\b/;

const browser = await chromium.launch(
  process.env.HTTPS_PROXY && !local ? { proxy: { server: process.env.HTTPS_PROXY } } : {},
);

// The live app's CDN sometimes answers a script chunk with 502 and the
// app stays on its splash screen; loading again helps.
async function openBackupSettings(page) {
  for (let attempt = 1; ; attempt += 1) {
    try {
      if (attempt === 1) {
        await page.goto(`${BASE}#/config`, { waitUntil: 'networkidle', timeout: 90_000 });
      } else {
        await page.reload({ waitUntil: 'networkidle', timeout: 90_000 });
      }
      await page.locator('[role=tab]').filter({ hasText: 'cloud_sync' }).click({ timeout: 30_000 });
      break;
    } catch (error) {
      if (attempt === 3) throw error;
      console.log(`settings did not load, attempt ${attempt}`);
    }
  }
  await page.getByText('Import/Export', { exact: true }).click();
  await page.locator('button').filter({ hasText: 'Import from File' }).waitFor();
}

/** Import one file in a fresh profile; returns what Super Productivity
 *  logged and showed, and saves its export to `out` when given. */
async function importFile(file, out) {
  const context = await browser.newContext({
    viewport: { width: 1200, height: 800 },
    acceptDownloads: true,
  });
  const page = await context.newPage();
  const seen = { repairs: [], dialogs: [], version: null };
  page.on('dialog', async (dialog) => {
    seen.dialogs.push(dialog.type());
    await dialog.dismiss();
  });
  let importing = false;
  page.on('console', (message) => {
    const text = message.text();
    if (importing && REPAIR.test(text) && !NOTHING.test(text)) {
      seen.repairs.push(text.replace(/\s+/g, ' ').slice(0, 200));
    }
  });
  try {
    await openBackupSettings(page);
    seen.version = (await page.locator('body').innerText()).match(
      /Super Productivity\s+(\d+\.\d+\.\d+)/,
    )?.[1];
    importing = true;
    await page.locator('input[type=file]').setInputFiles(file);
    await page.waitForURL(/#\/tag\/TODAY/, { timeout: 30_000 });
    await page.waitForTimeout(3000);
    importing = false;
    const open = await page.locator('mat-dialog-container').count();
    if (open) seen.dialogs.push(`${open} dialog(s) open after the import`);
    seen.menu = await page.locator('nav, side-nav, .side-nav').first().innerText();
    if (out) {
      await openBackupSettings(page);
      const [download] = await Promise.all([
        page.waitForEvent('download'),
        page.locator('button').filter({ hasText: /^\s*file_upload\s*Export Data\s*$/ }).click(),
      ]);
      await download.saveAs(out);
    }
  } finally {
    await context.close();
  }
  return seen;
}

let failed = 0;
const fail = (what) => {
  failed += 1;
  console.log(`FAIL: ${what}`);
};
const baselines = new Map();
try {
  for (const name of names) {
    const expect = JSON.parse(readFileSync(join(dir, `${name}.expect.json`), 'utf8'));
    let allowed = new Set();
    if (expect.baseline) {
      if (!baselines.has(expect.baseline)) {
        const base = join(dir, `${expect.baseline}.json`);
        if (!existsSync(base)) throw new Error(`baseline ${base} missing`);
        baselines.set(expect.baseline, await importFile(base, null));
      }
      allowed = new Set(baselines.get(expect.baseline).repairs);
    }
    const seen = await importFile(join(dir, `${name}.json`), join(dir, `${name}.sp.json`));
    console.log(`${name}: Super Productivity ${seen.version ?? 'unknown'}`);
    const extra = seen.repairs.filter((line) => !allowed.has(line));
    for (const line of new Set(extra)) fail(`${name}: repair: ${line}`);
    for (const dialog of seen.dialogs) fail(`${name}: dialog: ${dialog}`);
    for (const title of expect.projectTitles) {
      if (!seen.menu.includes(title)) fail(`${name}: a project is missing from the menu`);
    }
    if (!extra.length && !seen.dialogs.length) {
      console.log(
        `ok: ${name} imported without a repair` +
          (allowed.size ? ` (${allowed.size} log lines as for the unchanged fixture)` : ''),
      );
    }
  }
} finally {
  await browser.close();
}
process.exit(failed ? 1 : 0);
