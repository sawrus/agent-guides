#!/usr/bin/env bash

set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 <target_directory>"
  exit 1
fi

TARGET_ROOT="$1"

SOURCE_DIRS=(rules skills workflows)
TARGET_SUB_DIRS=(.agent .kilocode)

for target in "${TARGET_SUB_DIRS[@]}"; do
  TARGET_PATH="$TARGET_ROOT/$target"

  echo "Processing $TARGET_PATH"
  mkdir -p "$TARGET_PATH"

  for src in "${SOURCE_DIRS[@]}"; do
    if [ -d "$src" ]; then
      echo "  Copying $src -> $TARGET_PATH/"
      cp -a "$src" "$TARGET_PATH/"
    else
      echo "  Skipping $src (not found)"
    fi
  done
done

echo "Done."
