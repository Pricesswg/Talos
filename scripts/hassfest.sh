#!/usr/bin/env bash
# Run hassfest locally, in the same container CI uses, so a translation or a
# manifest problem is caught before the push instead of after it.
# Requires Docker to be running.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Start it and try again."
  exit 1
fi

docker run --rm -v "$PWD":/github/workspace ghcr.io/home-assistant/hassfest
