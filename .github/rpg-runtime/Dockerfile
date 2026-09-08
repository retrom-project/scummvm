FROM emscripten/emsdk@sha256:90b757eb11fa9a0e3ce4d2d9f76d932a56018e4accc37b5a28b2783751e60eb7
RUN apt-get update && apt-get install -y --no-install-recommends autoconf automake libtool pkg-config libpng-dev libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*
