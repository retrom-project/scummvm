#!/usr/bin/env python3
"""Run the real pinned SDL axis delivery and browser sampling functions together."""
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SDL = ROOT / ".retrom/em-cache/ports/sdl3/SDL-release-3.2.4/src/joystick"


def function(path, name):
    source = path.read_text()
    start = source.index(name)
    end = source.index("\n}", start) + 2
    return source[start:end]


class BrowserAxesTests(unittest.TestCase):
    def test_patch_is_idempotent_and_rejects_unknown_source(self):
        spec = importlib.util.spec_from_file_location("retrom_sdl3_patch", ROOT / ".github/rpg-runtime/prepare-sdl3.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = (SDL / "emscripten/SDL_sysjoystick.c").read_text()
        patched = module.patch_source(source)
        self.assertEqual(patched, module.patch_source(patched))
        with self.assertRaisesRegex(ValueError, "SOURCE_MISMATCH"):
            module.patch_source(source + "\n// unexpected source change")

    def test_first_movement_release_and_reopen_are_delivered(self):
        program = r'''
#include <cassert>
#include <cmath>
#include <cstdint>
#include <vector>
using Uint64 = uint64_t; using Uint8 = uint8_t; using Sint16 = int16_t;
#define SDL_assert assert
#define SDL_abs std::abs
#define SDL_JOYSTICK_AXIS_MAX 32767
#define SDL_EVENT_JOYSTICK_AXIS_MOTION 1
#define EMSCRIPTEN_RESULT_SUCCESS 0
struct SDL_JoystickAxisInfo {
 Sint16 initial_value=0,value=0,zero=0;
 bool has_initial_value=false,has_second_value=false,sent_initial_value=false,sending_initial_value=false;
};
struct SDL_Joystick {int naxes=2,guid=0,instance_id=1; SDL_JoystickAxisInfo axes[2]; void *hwdata=nullptr; Uint64 update_complete=0;};
struct SDL_Event {int type; struct {Uint64 timestamp;} common; struct {int which,axis,value;} jaxis;};
struct EmscriptenGamepadEvent {double timestamp=10,axis[2]={0,0},analogButton[1]={0},digitalButton[1]={0};} browser;
struct SDL_joylist_item {
 int index=0,naxes=2,nbuttons=0; double timestamp=10,axis[2]={0,0},analogButton[1]={0},digitalButton[1]={0}; SDL_Joystick *joystick;
};
std::vector<SDL_Event> events;
void SDL_AssertJoysticksLocked() {}
bool SDL_IsJoystickVIRTUAL(int) {return false;}
bool SDL_PrivateJoystickShouldIgnoreEvent() {return false;}
bool SDL_EventEnabled(int) {return true;}
void SDL_PushEvent(SDL_Event *event) {events.push_back(*event);}
void SDL_SendJoystickButton(Uint64,SDL_Joystick*,int,bool) {}
Uint64 SDL_GetTicksNS() {return 1;}
void emscripten_sample_gamepad_data() {}
int emscripten_get_gamepad_status(int,EmscriptenGamepadEvent *state) {*state=browser;return 0;}
DELIVERY
SAMPLING
void checkSession() {
 SDL_Joystick joystick; SDL_joylist_item item; item.joystick=&joystick; joystick.hwdata=&item;
 browser=EmscriptenGamepadEvent(); events.clear();
 EMSCRIPTEN_JoystickUpdate(&joystick); // unchanged timestamp must still initialize axes
 assert(joystick.axes[0].has_initial_value && joystick.axes[1].has_initial_value);
 assert(events.empty());
 browser.axis[0]=1; browser.timestamp++;
 EMSCRIPTEN_JoystickUpdate(&joystick);
 assert(!events.empty() && events.back().jaxis.axis==0 && events.back().jaxis.value==32767);
 browser.axis[0]=0; browser.timestamp++;
 EMSCRIPTEN_JoystickUpdate(&joystick);
 assert(events.back().jaxis.value==0);
 browser.axis[1]=-1; browser.timestamp++;
 EMSCRIPTEN_JoystickUpdate(&joystick);
 assert(events.back().jaxis.axis==1 && events.back().jaxis.value==-32767);
 auto count=events.size(); EMSCRIPTEN_JoystickUpdate(&joystick); assert(events.size()==count);
}
int main() {checkSession(); checkSession();}
'''
        program = program.replace("DELIVERY", function(SDL / "SDL_joystick.c", "void SDL_SendJoystickAxis("))
        program = program.replace("SAMPLING", function(SDL / "emscripten/SDL_sysjoystick.c", "static void EMSCRIPTEN_JoystickUpdate("))
        with tempfile.TemporaryDirectory() as directory:
            source, binary = Path(directory) / "axes.cpp", Path(directory) / "axes"
            source.write_text(program)
            subprocess.run(["c++", "-std=c++11", "-Wall", "-Wextra", "-Werror", str(source), "-o", str(binary)],
                           check=True, capture_output=True, timeout=30)
            subprocess.run([str(binary)], check=True, capture_output=True, timeout=5)


if __name__ == "__main__":
    unittest.main()
