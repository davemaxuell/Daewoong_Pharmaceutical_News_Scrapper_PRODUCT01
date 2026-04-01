#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
NODE_BIN="$PROJECT_ROOT/.tools/node/bin/node"
TARGET_FILE="$PROJECT_ROOT/src/admin_api/static/admin.js"

if [ ! -x "$NODE_BIN" ]; then
  echo "Local Node runtime not found at $NODE_BIN" >&2
  echo "Install it first, or restore the local .tools/node runtime." >&2
  exit 1
fi

"$NODE_BIN" --check "$TARGET_FILE"
echo "JS syntax OK: $TARGET_FILE"
