#!/usr/bin/env bash
# Start POX with our controller. POX location: $POX_DIR (default ~/pox).
HERE="$(cd "$(dirname "$0")" && pwd)"
POX_DIR="${POX_DIR:-$HOME/pox}"
PYTHONPATH="$HERE" exec python3 "$POX_DIR/pox.py" log.level --INFO \
    openflow.of_01 --port=6633 adaptive
