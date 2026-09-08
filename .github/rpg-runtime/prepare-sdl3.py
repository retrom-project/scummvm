#!/usr/bin/env python3
"""Apply the bounded Retrom input fix to the pinned Emscripten SDL 3 port."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "src/joystick/emscripten/SDL_sysjoystick.c"
ORIGINAL_SHA256 = "40b54d9ab85f9eb0967eec55e04e5deb039b1066c9c5f9bf0b43819b4b9f0154"
ANCHOR = "        if (result == EMSCRIPTEN_RESULT_SUCCESS) {\n"
SEED = '''            // Retrom: initialize every axis even when the browser timestamp is unchanged.
            // Otherwise SDL treats the first movement as its initial position and drops it.
            for (i = 0; i < item->naxes; i++) {
                if (!joystick->axes[i].has_initial_value) {
                    SDL_SendJoystickAxis(timestamp, joystick, i, (Sint16)(32767.f * gamepadState.axis[i]));
                }
            }
'''


def patch_source(source):
    original = source.replace(ANCHOR + SEED, ANCHOR)
    if hashlib.sha256(original.encode()).hexdigest() != ORIGINAL_SHA256:
        raise ValueError("RETROM_SDL3_SOURCE_MISMATCH")
    if original.count(ANCHOR) != 1:
        raise ValueError("RETROM_SDL3_PATCH_BOUNDARY_MISMATCH")
    return original.replace(ANCHOR, ANCHOR + SEED)


def main():
    cache = (ROOT / ".retrom/em-cache").resolve()
    if Path(os.environ["EM_CACHE"]).resolve() != cache:
        raise ValueError("RETROM_SDL3_CACHE_SCOPE_MISMATCH")
    # Fetch via the pinned SDK port recipe, including its SHA-512 archive verification.
    sdk = Path(subprocess.check_output(["which", "emcc"], text=True).strip()).resolve().parent
    sys.path.insert(0, str(sdk))
    from tools import ports
    from tools.ports import sdl3
    if sdl3.VERSION != "3.2.4":
        raise ValueError("RETROM_SDL3_VERSION_MISMATCH")
    ports.Ports.fetch_project("sdl3", f"https://github.com/libsdl-org/SDL/archive/{sdl3.TAG}.zip", sha512hash=sdl3.HASH)
    path = cache / "ports/sdl3" / sdl3.SUBDIR / SOURCE
    before = path.read_text()
    after = patch_source(before)
    if after == before:
        return
    path.write_text(after)
    # Invalidate only this worktree's SDL libraries and final link after a changed patch.
    for library in (cache / "sysroot/lib").rglob("libSDL3*.a"):
        library.unlink()
    (ROOT / ".retrom/web/scummvm.mjs").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
