#!/bin/sh
# The whole real-app test (docs/dev-environment.md, real app): write
# Pensum's exports, import them into Super Productivity, read its exports
# back into Pensum, and check that a broken export is rejected.
#
#   tests/real_app/run.sh [OUT_DIR]
#
# PENSUM_SP_URL picks the Super Productivity (default: the live web app),
# PYTHON the interpreter (default: python3; the store needs no PyGObject).
set -eu
here=$(dirname "$0")
out=${1:-$here/out}
python=${PYTHON:-python3}

"$python" "$here/make_exports.py" "$out" --broken
node "$here/sp_import.mjs" "$out" fixture fresh demo imported
"$python" "$here/check_round_trip.py" "$out" fixture fresh demo imported
if node "$here/sp_import.mjs" "$out" broken; then
  echo "FAIL: the broken export (a task in a missing project) was accepted"
  exit 1
fi
echo "ok: the broken export was rejected"
