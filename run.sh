#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

export MAP_SIDE_SEP_MM=475
export MAP_MM_PER_PX=0.05

exec ./venv/bin/python app.py