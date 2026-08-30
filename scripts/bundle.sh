#!/usr/bin/env bash
# Copy the standalone core into the integration for a HACS release.
# The core lives at the repository root so CI can test it without Home
# Assistant; HACS installs only what is under custom_components.
set -euo pipefail
cd "$(dirname "$0")/.."

VENDOR="custom_components/talos/vendor"
rm -rf "$VENDOR"
mkdir -p "$VENDOR"
cp -R talos_core "$VENDOR/talos_core"
find "$VENDOR" -name '__pycache__' -type d -prune -exec rm -rf {} +
touch "$VENDOR/__init__.py"
echo "bundled talos_core -> $VENDOR/talos_core"
