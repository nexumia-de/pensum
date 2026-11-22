// The sync test's Git Sync step (run_sync.sh, scenario git): runs one step
// of the cycle of the Super Productivity plugin in nexumia-de/tabularium
// (src/git-cycle.cjs, the code the plugin hands to executeNodeScript) on
// the desktop's sync folder. Super Productivity's sync between `prepare`
// and `finish` is sp_sync.mjs, standing in for the plugin's triggerSync.
//
//   TABULARIUM=DIR node tests/real_app/git_cycle.mjs prepare|finish FOLDER [TOOK]
//
// TOOK: the number of Day Planner hand-overs `prepare` must take.
import { createRequire } from 'node:module';
import { join, resolve } from 'node:path';

const [step, folder, took] = process.argv.slice(2);
const tabularium = process.env.TABULARIUM;
if (!tabularium || !['prepare', 'finish'].includes(step) || !folder) {
  console.error('usage: TABULARIUM=DIR node git_cycle.mjs prepare|finish FOLDER [TOOK]');
  process.exit(2);
}
const { run } = createRequire(import.meta.url)(join(resolve(tabularium), 'src', 'git-cycle.cjs'));
const result = await run({ step, folder: resolve(folder), git: 'git' });
console.log(`git ${step}: ${JSON.stringify(result)}`);
if (!result.ok) process.exit(1);
if (took !== undefined && result.took !== Number(took)) {
  console.log(`FAIL: took ${result.took} hand-overs, expected ${took}`);
  process.exit(1);
}
