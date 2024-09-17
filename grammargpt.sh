#!/bin/bash
cd "$(dirname "$0")" || exit
. ./.env
if [ -z "$MODEL" ]; then
  echo "Please set the MODEL environment variable"
  exit 1
fi
pipenv run ./clipboardgpt.py --type grammar --model "${MODEL}" $@