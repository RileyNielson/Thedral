#!/bin/bash
# Same app as Run_Thedral.command, with the optional local AI helper (Ollama) turned on.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THEDRAL_MODE=FULL exec "$DIR/Run_Thedral.command" "$@"
