// The sync test's Git Sync step (run_sync.sh, scenario git): runs one step
// of the cycle of the Super Productivity plugin in nexumia-de/tabularium
// (its src/cycle.js through scripts/build.mjs' loadEngine, in its stand-in
// for Super Productivity's plugin host, scripts/host.mjs) on the
// desktop's sync folder, against the GitHub stand-in at PENSUM_GITHUB_API
// (tests/github_fake.py). Super Productivity's sync between `prepare` and
// `finish` is sp_sync.mjs, standing in for the plugin's triggerSync. The
// plugin's per-device state is kept in FOLDER/../git-sync-secrets.json.
//
//   TABULARIUM=DIR node tests/real_app/git_cycle.mjs prepare|finish FOLDER [TOOK]
//
// TOOK: the number of Day Planner hand-overs `prepare` must take.
import { dirname, join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const [step, folderArg, took] = process.argv.slice(2);
const tabularium = process.env.TABULARIUM;
const api = process.env.PENSUM_GITHUB_API;
if (!tabularium || !api || !['prepare', 'finish'].includes(step) || !folderArg) {
  console.error('usage: TABULARIUM=DIR PENSUM_GITHUB_API=URL node git_cycle.mjs prepare|finish FOLDER [TOOK]');
  process.exit(2);
}
const folder = resolve(folderArg);
const load = (name) => import(pathToFileURL(join(resolve(tabularium), 'scripts', name)).href);
const { loadEngine } = await load('build.mjs');
const { createHost } = await load('host.mjs');
const host = createHost({ secretsFile: join(dirname(folder), 'git-sync-secrets.json') });
const engine = loadEngine(host);
const saved = await host.getSecret('state');
const ctx = {
  folder,
  repository: 'test/sync',
  github: engine.githubClient('test', 'test/sync', api),
  state: saved ? JSON.parse(saved) : null,
  saveState(next) {
    ctx.state = next;
    host.setSecret('state', JSON.stringify(next));
  },
};
let result;
try {
  result = step === 'prepare' ? await engine.cyclePrepare(ctx) : await engine.cycleFinish(ctx);
} catch (error) {
  console.log(`FAIL: Git Sync ${step}: ${error.code || error.message}`);
  process.exit(1);
}
console.log(`Git Sync ${step}: ${JSON.stringify(result)}`);
if (took !== undefined && result.took !== Number(took)) {
  console.log(`FAIL: took ${result.took} hand-overs, expected ${took}`);
  process.exit(1);
}
