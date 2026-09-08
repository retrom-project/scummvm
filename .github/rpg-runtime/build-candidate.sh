#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
output=${1:?usage: build-candidate.sh ABSOLUTE_EMPTY_OUTPUT}
bash "$root/.github/rpg-runtime/build-assets.sh" "$output"
python3 "$root/.github/rpg-runtime/candidate_descriptor.py" finalize "$output" --core-id scummvm
