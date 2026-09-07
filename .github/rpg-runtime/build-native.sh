#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
mkdir -p "$root/.retrom/native"
cd "$root/.retrom/native"
# SCI and Wintermute use their execution plugins for upstream fallback detection.
# Keep these in the server detector, even though no game is ever run there.
../../configure --backend=null --disable-all-engines --enable-engine=sci,sci32,wintermute \
  --enable-detection-full --disable-debug --disable-alsa --disable-seq-midi \
  --disable-cloud --disable-system-dialogs --disable-tts --disable-sndio --disable-libcurl \
  --disable-fribidi --disable-freetype2 --disable-gtk
make -j"${RETROM_BUILD_JOBS:-4}"
