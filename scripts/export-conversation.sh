#!/bin/bash
# Wrapper script - delegates to Python for all logic
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/export-conversation.py" "$@"
