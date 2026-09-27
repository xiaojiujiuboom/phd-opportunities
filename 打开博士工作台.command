#!/bin/zsh
cd "$(dirname "$0")" || exit 1
python3 scraper/bundle.py || exit 1
open index.html
