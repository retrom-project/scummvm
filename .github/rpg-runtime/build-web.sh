#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$root"
export EM_CACHE="$root/.retrom/em-cache"
prefix="$root/.retrom/libs/install"
mkdir -p "$prefix" "$root/.retrom/web"
if [[ ! -f "$prefix/lib/libmad.a" ]]; then
  tar -xf .retrom/libs/libmad-0.15.1b.tar.gz -C .retrom/libs
  (
    cd .retrom/libs/libmad-0.15.1b
    sed -i 's/-fforce-mem//g' configure
    CFLAGS='-fPIC -Oz' emconfigure ./configure --host=wasm32-unknown-none --build=wasm32-unknown-none --prefix="$prefix" --enable-fpm=no --disable-shared
    emmake make -j4
    emmake make install
  )
fi
if [[ ! -f "$prefix/lib/libtheoradec.a" ]]; then
  tar -xf .retrom/libs/libtheora-1.1.1.tar.bz2 -C .retrom/libs
  (
    cd .retrom/libs/libtheora-1.1.1
    CFLAGS='-fPIC -sUSE_OGG=1 -Oz' emconfigure ./configure --host=wasm32-unknown-none --build=wasm32-unknown-none --prefix="$prefix" --disable-asm --disable-examples --disable-encode --disable-shared
    emmake make -j4
    emmake make install
  )
fi
if [[ ! -f "$prefix/lib/libmpeg2.a" ]]; then
  tar -xf .retrom/libs/libmpeg2.tar.gz -C .retrom/libs
  (
    cd .retrom/libs/libmpeg2-946bf4b518aacc224f845e73708f99e394744499
    autoreconf -i
    CFLAGS='-fPIC -Oz' emconfigure ./configure --host=wasm32-unknown-none --build=wasm32-unknown-none --prefix="$prefix" --disable-sdl --disable-shared
    emmake make -j4
    emmake make install
  )
fi
engines=$(python3 -c 'import json; v=json.load(open(".github/rpg-runtime/build-lock.json")); print(",".join(e["id"] for e in v["engines"] if e["enabled"]))')
cd .retrom/web
emconfigure ../../configure --host=wasm32-unknown-emscripten --build=wasm32-unknown-emscripten \
  --enable-retrom-host --enable-plugins --default-dynamic --enable-detection-static --enable-detection-full \
  --disable-all-engines "--enable-engine=$engines" --disable-debug \
  --enable-freetype2 --enable-gif --enable-jpeg --enable-ogg --enable-png --enable-vorbis --enable-zlib \
  "--with-mad-prefix=$prefix" "--with-theoradec-prefix=$prefix" "--with-mpeg2-prefix=$prefix"
emmake make -j"${RETROM_BUILD_JOBS:-6}"
