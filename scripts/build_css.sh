#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
npx tailwindcss -i static/css/input.css -o static/css/dist.css --minify
