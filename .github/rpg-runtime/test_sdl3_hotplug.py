#!/usr/bin/env python3
"""Execute ScummVM's SDL3 device handlers with real instance-ID semantics."""
import unittest
from test_canvas_resize import execute, function


class HotplugTests(unittest.TestCase):
    def test_late_connection_reconnection_and_device_selection(self):
        path = 'backends/events/sdl/sdl3-events.cpp'
        handlers = '\n'.join(function(path, signature) for signature in (
            'void SdlEventSource::openJoystick(', 'void SdlEventSource::closeJoystick(',
            'bool SdlEventSource::handleJoystickAdded(', 'bool SdlEventSource::handleJoystickRemoved('))
        execute(r'''
#include <cassert>
// The old handler compares signed ordinals with unsigned IDs; reach its behavioral assertion.
#pragma GCC diagnostic ignored "-Wsign-compare"
#include <cstdlib>
#include <vector>
using SDL_JoystickID = unsigned int;
struct SDL_Joystick {SDL_JoystickID id;};
struct SDL_Gamepad {SDL_Joystick joystick;};
struct SDL_JoyDeviceEvent {SDL_JoystickID which;};
namespace Common {enum {EVENT_INPUT_CHANGED=1}; struct Event {int type=0;};}
struct Config {int selected=0; int getInt(const char *) {return selected;}} ConfMan;
std::vector<SDL_JoystickID> connected;
int opens=0, closes=0; bool gamepad=true, failOpen=false;
template<class... T> void debug(T...) {}
template<class... T> void warning(T...) {}
const char *SDL_GetError() {return "test";}
SDL_JoystickID *SDL_GetJoysticks(int *count) {
 *count=connected.size(); auto ids=new SDL_JoystickID[*count+1]();
 for(int i=0;i<*count;++i) {ids[i]=connected[i];}
 return ids;
}
void SDL_free(SDL_JoystickID *ids) {delete[] ids;}
bool SDL_IsGamepad(SDL_JoystickID) {return gamepad;}
SDL_Gamepad *SDL_OpenGamepad(SDL_JoystickID id) {++opens; return failOpen?nullptr:new SDL_Gamepad{{id}};}
SDL_Joystick *SDL_OpenJoystick(SDL_JoystickID id) {++opens; return failOpen?nullptr:new SDL_Joystick{id};}
const char *SDL_GetGamepadName(SDL_Gamepad *) {return "pad";}
const char *SDL_GetJoystickName(SDL_Joystick *) {return "stick";}
void SDL_CloseGamepad(SDL_Gamepad *pad) {++closes; delete pad;}
void SDL_CloseJoystick(SDL_Joystick *pad) {++closes; delete pad;}
SDL_Joystick *SDL_GetGamepadJoystick(SDL_Gamepad *pad) {return &pad->joystick;}
SDL_JoystickID SDL_GetJoystickID(SDL_Joystick *stick) {return stick->id;}
struct SdlEventSource {
 SDL_Gamepad *_controller=nullptr; SDL_Joystick *_joystick=nullptr;
 void openJoystick(int); void closeJoystick();
 bool handleJoystickAdded(const SDL_JoyDeviceEvent &, Common::Event &);
 bool handleJoystickRemoved(const SDL_JoyDeviceEvent &, Common::Event &);
};
FUNCTIONS
void session(bool controller) {
 gamepad=controller; opens=closes=0; ConfMan.selected=0; connected.clear();
 SdlEventSource source; Common::Event event;
 source.openJoystick(0); assert(opens==0);
 connected={42}; // SDL3 emits a nonzero instance ID, never the ordinal 0.
 assert(source.handleJoystickAdded({42},event)); assert(opens==1 && event.type==Common::EVENT_INPUT_CHANGED);
 event.type=0;
 assert(!source.handleJoystickAdded({42},event)); assert(opens==1 && closes==0 && event.type==0);
 connected={42,73}; assert(!source.handleJoystickAdded({73},event)); assert(opens==1);
 assert(!source.handleJoystickRemoved({73},event)); assert(closes==0);
 connected.clear(); assert(source.handleJoystickRemoved({42},event)); assert(closes==1);
 connected={101}; assert(source.handleJoystickAdded({101},event)); assert(opens==2);
 source.closeJoystick();
 ConfMan.selected=-1; event.type=0;
 assert(!source.handleJoystickAdded({101},event)); source.openJoystick(-1); assert(opens==2 && event.type==0);
 ConfMan.selected=1; assert(!source.handleJoystickAdded({101},event));
 connected={101,202}; assert(!source.handleJoystickAdded({101},event));
 assert(source.handleJoystickAdded({202},event)); assert(opens==3); source.closeJoystick();
 failOpen=true; event.type=0; assert(!source.handleJoystickAdded({202},event)); assert(event.type==0); failOpen=false;
 // SDL also queues add events for controllers already opened during initialization.
 source.openJoystick(1); int before=opens;
 assert(!source.handleJoystickAdded({202},event)); assert(opens==before); source.closeJoystick();
}
int main() {session(true); session(false);}
'''.replace('FUNCTIONS', handlers))


if __name__ == '__main__':
    unittest.main()
