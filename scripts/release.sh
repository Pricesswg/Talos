#!/usr/bin/env bash
# Bump the version, bundle the core, commit, tag, push, create the release.
# Usage: ./scripts/release.sh <version> "<release notes>"
#   e.g. ./scripts/release.sh 0.2.0 "Motore dei controlli di postura"

set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <version> \"<release notes>\""
  exit 1
fi

VERSION="$1"
NOTES="$2"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ "$BRANCH" != "main" ]; then
  echo "Not on main (currently on $BRANCH). Aborting."
  exit 1
fi

if git rev-parse "v$VERSION" >/dev/null 2>&1; then
  echo "Tag v$VERSION already exists locally."
  exit 1
fi

echo "==> Syncing with the remote"
git fetch origin
if git ls-remote --tags origin "v$VERSION" | grep -q "v$VERSION"; then
  echo "Tag v$VERSION already exists on the remote. Aborting."
  exit 1
fi

echo "==> Running the suite"
python3 -m unittest discover -s tests -t .

echo "==> Bumping to $VERSION"
python3 - "$VERSION" <<'PY'
import json, pathlib, re, sys
version = sys.argv[1]
manifest = pathlib.Path("custom_components/talos/manifest.json")
data = json.loads(manifest.read_text())
data["version"] = version
manifest.write_text(json.dumps(data, indent=2) + "\n")

for path, pattern in (
    (pathlib.Path("pyproject.toml"), r'(?m)^version = ".*"$'),
    (pathlib.Path("talos_core/__init__.py"), r'(?m)^__version__ = ".*"$'),
):
    text = path.read_text()
    replacement = f'version = "{version}"' if path.suffix == ".toml" else f'__version__ = "{version}"'
    path.write_text(re.sub(pattern, replacement, text, count=1))
print(f"version -> {version}")
PY

echo "==> Bundling the core for HACS"
./scripts/bundle.sh

# The vendored copy is gitignored on purpose: the source of truth is
# talos_core/ at the root, and the release archive is built from the tag.
git add -A
git commit -m "Release v$VERSION

$NOTES"
git tag -a "v$VERSION" -m "v$VERSION"
git push origin main --follow-tags

if command -v gh >/dev/null 2>&1; then
  gh release create "v$VERSION" --title "v$VERSION" --notes "$NOTES"
else
  echo "gh not installed: create the GitHub release by hand."
fi
echo "==> v$VERSION released"
