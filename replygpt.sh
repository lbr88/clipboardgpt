#!/bin/bash

cd "$(dirname "$0")" || exit
. ./.env
if [ -z "$NAME" ]; then
  echo "Please set the NAME environment variable"
  exit 1
fi
if [ -z "$MODEL" ]; then
  echo "Please set the MODEL environment variable"
  exit 1
fi
pipenv run ./clipboardgpt.py --type "reply" --model "${MODEL}" --context "My name is ${NAME}" $@
