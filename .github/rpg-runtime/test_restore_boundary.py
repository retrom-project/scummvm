#!/usr/bin/env python3
"""Execute the native restore notification guard, including old-source regression."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "backends/platform/sdl/emscripten/retrom-host.cpp"


def restore_function():
    reference = os.environ.get("SCUMMVM_TEST_SOURCE_REF")
    source = (subprocess.check_output(["git", "show", f"{reference}:{SOURCE}"], cwd=ROOT, text=True)
              if reference else (ROOT / SOURCE).read_text())
    start = source.index("void restoreResult(int slot, bool success) {")
    end = source.index("\nvoid engineStopping()", start)
    return source[start:end]


class RestoreBoundaryTests(unittest.TestCase):
    def test_reports_only_explicit_slot_once_and_quits_on_failed_restore(self):
        program = '''
#include <cassert>
struct Config {
 bool present = true; int slot = 7;
 bool hasKey(const char *) {return present;}
 int getInt(const char *) {return slot;}
} ConfMan;
struct Engine {static int quits; static void quitGame() {++quits;}};
int Engine::quits = 0;
bool restoreReported = false;
int calls = 0, reportedSlot = -1; bool reportedSuccess = false;
void retromRestoreResult(int slot, bool success) {
 ++calls; reportedSlot = slot; reportedSuccess = success;
}
FUNCTION
int main() {
 ConfMan.present = false; restoreResult(7, true); assert(calls == 0);
 ConfMan.present = true; restoreResult(8, true); assert(calls == 0);
 restoreResult(7, true); assert(calls == 1 && reportedSlot == 7 && reportedSuccess);
 restoreResult(7, false); assert(calls == 1 && Engine::quits == 0);
 restoreReported = false; restoreResult(7, false);
 assert(calls == 2 && !reportedSuccess && Engine::quits == 1);
}
'''.replace("FUNCTION", restore_function())
        with tempfile.TemporaryDirectory() as directory:
            cpp, binary = Path(directory) / "restore.cpp", Path(directory) / "restore"
            cpp.write_text(program)
            subprocess.run(["c++", "-std=c++11", "-Wall", "-Wextra", "-Werror", str(cpp), "-o", str(binary)],
                           check=True, capture_output=True, timeout=30)
            subprocess.run([str(binary)], check=True, capture_output=True, timeout=5)


if __name__ == "__main__":
    unittest.main()
