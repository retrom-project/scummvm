#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$root"
output=${1:?usage: build-candidate.sh ABSOLUTE_EMPTY_OUTPUT}
python3 .github/rpg-runtime/candidate_descriptor.py prepare "$output"
python3 .github/rpg-runtime/fetch-inputs.py
python3 .github/rpg-runtime/test_web_javascript.py
python3 .github/rpg-runtime/test_restore_boundary.py
python3 .github/rpg-runtime/test_canvas_resize.py
image="retrom-scummvm-toolchain:$(sha256sum .github/rpg-runtime/Dockerfile | cut -c1-16)"
docker build -t "$image" -f .github/rpg-runtime/Dockerfile .
docker run --rm --user "$(id -u):$(id -g)" -v "$root:$root" -w "$root" "$image" \
  bash .github/rpg-runtime/build-native.sh
python3 .github/rpg-runtime/test_detector.py
if readelf -l .retrom/native/scummvm | grep -q 'INTERP'; then
  echo 'Retrom detector must be statically linked' >&2
  exit 1
fi
docker run --rm --user "$(id -u):$(id -g)" -v "$root:$root" -w "$root" "$image" \
  bash .github/rpg-runtime/build-web.sh
stage=$(mktemp -d "$root/.retrom/package.XXXXXXXX")
trap 'rm -rf "$stage"' EXIT
python3 .github/rpg-runtime/package.py "$stage" --archive "$output/scummvm-runtime.zip"
python3 .github/rpg-runtime/candidate_descriptor.py finalize "$output" --core-id scummvm
