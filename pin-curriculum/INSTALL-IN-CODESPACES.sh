#!/usr/bin/env bash
set -euo pipefail

# Run from any working directory; operate only inside this script's folder.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

npm install
npm run validate:pin
npm run validate:atlas
npm test
