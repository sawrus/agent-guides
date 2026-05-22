#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
IMAGE="${AGENTIC_UBUNTU_BLACKBOX_IMAGE:-ubuntu:24.04}"

if ! command -v docker >/dev/null 2>&1; then
  echo "[ubuntu-blackbox-e2e][FAIL] docker is required" >&2
  exit 127
fi

docker run --rm \
  -v "$ROOT_DIR:/workspace/agent-guides:ro" \
  -w /workspace/agent-guides \
  -e DEBIAN_FRONTEND=noninteractive \
  "$IMAGE" \
  bash -euxo pipefail -c '
    apt-get update
    apt-get install -y --no-install-recommends \
      bash \
      ca-certificates \
      coreutils \
      git \
      grep \
      make \
      nodejs \
      npm \
      python3 \
      python3-pip \
      sed

    ./agentic --version
    make test
  '

echo 'ubuntu blackbox e2e ok'
