#!/bin/bash

cd "$(dirname "$0")" || exit
# shellcheck disable=SC1091
. ./.env
if [ -z "$NAME" ]; then
  echo "Please set the NAME environment variable"
  exit 1
fi
if [ -z "$MODEL" ]; then
  echo "Please set the MODEL environment variable"
  exit 1
fi
uv run ./clipboardgpt.py --type "reply" --model "${MODEL}" --context "Use my name to sign off the message if it's an email otherwise don't use my name: My name: ${NAME}" "$@"
