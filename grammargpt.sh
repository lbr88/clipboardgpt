#!/bin/bash
cd "$(dirname "$0")" || exit
# shellcheck disable=SC1091
. ./.env
if [ -z "$MODEL" ]; then
  echo "Please set the MODEL environment variable"
  exit 1
fi
uv run ./clipboardgpt.py --type grammar --model "${MODEL}" "$@"