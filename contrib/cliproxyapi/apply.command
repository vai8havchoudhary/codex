#!/bin/sh
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python=${PYTHON:-python3}
"$python" "$script_dir/install.py" --dry-run "$@"
exec "$python" "$script_dir/install.py" "$@"
