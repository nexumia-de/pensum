#!/bin/sh
# The sync test (docs/dev-environment.md, sync test): a WebDAV test
# server, Super Productivity syncing to it (sp_sync.mjs), and Pensum
# reading the folder (check_sync.py), in two rounds; check_sync.py also
# checks that wrong decodes fail and that reading changes no file. Runs
# three times: plain files, compressed and encrypted ones (#29), and the
# split v3 files whose ops Pensum replays (#30).
#
#   tests/real_app/run_sync.sh [OUT_DIR]
#
# PENSUM_SP_URL picks the Super Productivity (default: the live web app),
# PYTHON the interpreter for Pensum (default: python3), WSGIDAV the WebDAV
# server command (default: wsgidav, pinned in requirements-webdav.txt).
set -eu
here=$(cd "$(dirname "$0")" && pwd)
out=${1:-$here/out-sync}
python=${PYTHON:-python3}
wsgidav=${WSGIDAV:-wsgidav}

rm -rf "$out"
mkdir -p "$out/dav"
"$wsgidav" --config "$here/wsgidav.yaml" --root "$out/dav" > "$out/webdav.log" 2>&1 &
dav_pid=$!
trap 'kill $dav_pid 2>/dev/null || true' EXIT INT TERM
i=0
until curl -s -o /dev/null -u test:test http://127.0.0.1:2345/; do
  i=$((i + 1))
  [ $i -lt 30 ] || { echo "FAIL: the WebDAV server did not start"; cat "$out/webdav.log"; exit 1; }
  sleep 1
done
export PENSUM_DAV_URL=http://127.0.0.1:2345/ PENSUM_DAV_ROOT="$out/dav"

# scenario NAME SPLIT COMPRESS PASSWORD
scenario() {
  echo "== $1"
  export PENSUM_DAV_FOLDER="$1" PENSUM_SYNC_SPLIT="$2" PENSUM_SYNC_COMPRESS="$3" \
    PENSUM_SYNC_PASSWORD="$4"
  mkdir -p "$out/$1"
  for round in 1 2; do
    node "$here/sp_sync.mjs" "$out/$1" $round
    "$python" "$here/check_sync.py" "$out/$1" $round
  done
}

scenario plain "" "" ""
scenario encrypted "" 1 "test password"
# Surgical sync (v3): the snapshot lags behind, so reading needs the
# replay of the ops after it (#30).
scenario split 1 "" ""
