#!/usr/bin/env python3
"""Execute the native drawing and pause boundaries against browser resize races."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def function(path, signature):
    reference = os.environ.get("SCUMMVM_TEST_SOURCE_REF")
    source = (subprocess.check_output(["git", "show", f"{reference}:{path}"], cwd=ROOT, text=True)
              if reference else (ROOT / path).read_text())
    start = source.index(signature)
    position = source.index("{", start) + 1
    depth = 1
    while depth:
        depth += (source[position] == "{") - (source[position] == "}")
        position += 1
    return source[start:position]


def execute(program):
    with tempfile.TemporaryDirectory() as directory:
        cpp, binary = Path(directory) / "resize.cpp", Path(directory) / "resize"
        cpp.write_text(program)
        subprocess.run(["c++", "-std=c++11", "-Wall", "-Wextra", "-Werror", str(cpp), "-o", str(binary)],
                       check=True, capture_output=True, timeout=30)
        subprocess.run([str(binary)], check=True, capture_output=True, timeout=5)


class CanvasResizeTests(unittest.TestCase):
    def test_draw_uses_current_canvas_even_before_sdl_delivers_resize(self):
        draw = function("backends/graphics/openglsdl/openglsdl-graphics.cpp",
                        "void OpenGLSdlGraphicsManager::updateScreen()")
        execute('''
#include <cassert>
#define EMSCRIPTEN 1
#define RETROM_HOST 1
#define SDL_VERSION_ATLEAST(a, b, c) 0
#define EMSCRIPTEN_RESULT_SUCCESS 0
int canvasWidth = 1920, canvasHeight = 1080, canvasResult = 0;
int emscripten_get_canvas_element_size(const char *, int *w, int *h) {
 *w = canvasWidth; *h = canvasHeight; return canvasResult;
}
struct OpenGLGraphicsManager {
 int _windowWidth = 1280, _windowHeight = 720, draws = 0, resizes = 0;
 void updateScreen() {
  if (canvasResult == 0 && canvasWidth > 0 && canvasHeight > 0)
   assert(_windowWidth == canvasWidth && _windowHeight == canvasHeight);
  ++draws;
 }
 void handleResize(int w, int h) {_windowWidth = w; _windowHeight = h; ++resizes;}
};
struct OpenGLSdlGraphicsManager : OpenGLGraphicsManager {
 int _ignoreResizeEvents = 0;
 void updateScreen();
};
FUNCTION
int main() {
 OpenGLSdlGraphicsManager graphics;
 graphics.updateScreen(); assert(graphics.resizes == 1);
 graphics.updateScreen(); assert(graphics.resizes == 1);
 canvasWidth = 900; canvasHeight = 600;
 graphics.updateScreen(); assert(graphics.resizes == 2);
 canvasWidth = canvasHeight = 0; graphics.updateScreen();
 assert(graphics.resizes == 2 && graphics._windowWidth == 900);
 canvasResult = -4; canvasWidth = 1920; canvasHeight = 1080;
 graphics.updateScreen(); assert(graphics.resizes == 2);
 assert(graphics.draws == 5);
}
'''.replace("FUNCTION", draw))

    def test_pause_keeps_presentation_current_without_resuming_engine(self):
        poll = function("backends/platform/sdl/emscripten/retrom-host.cpp", "void poll()")
        execute('''
#include <cassert>
bool running = true, polling = false, paused = true;
int pendingSlot = -1, openSaves = 0, sleeps = 0;
bool enginePaused = false;
struct PauseToken {void clear() {enginePaused = false;}};
struct MetaEngine {
 enum {kSupportsListSaves, kSupportsLoadingDuringStartup};
 bool hasFeature(int) const {return true;}
};
struct Engine {
 enum {kSupportsSavingDuringRuntime};
 MetaEngine meta;
 const MetaEngine *getMetaEngine() {return &meta;}
 bool hasFeature(int) {return true;}
 bool canSaveGameStateCurrently() {return true;}
 PauseToken pauseEngine() {enginePaused = true; return PauseToken();}
 static void quitGame() {assert(false);}
} engine;
Engine *g_engine = &engine;
struct System {
 int width = 1280, canvasWidth = 1920, updates = 0;
 void updateScreen() {assert(enginePaused); width = canvasWidth; ++updates;}
} systemState;
System *g_system = &systemState;
void finishSave(const MetaEngine &) {}
void saveAtBoundary(const MetaEngine &, bool) {assert(false);}
void retromStatus(bool, bool, bool) {}
bool hasRestoreResult() {return true;}
int retromCommand() {return 0;}
bool retromShouldPause() {return paused;}
void retromBoundary() {}
void retromPaused(int value) {
 if (value) assert(systemState.width == systemState.canvasWidth && enginePaused);
 else assert(!enginePaused);
}
void emscripten_sleep(int) {
 assert(enginePaused && systemState.width == systemState.canvasWidth);
 if (++sleeps == 3) paused = false;
 else systemState.canvasWidth = sleeps == 1 ? 900 : 1920;
}
FUNCTION
int main() {
 poll();
 assert(!enginePaused && !polling && sleeps == 3 && systemState.updates >= 3);
}
'''.replace("FUNCTION", poll))


if __name__ == "__main__":
    unittest.main()
