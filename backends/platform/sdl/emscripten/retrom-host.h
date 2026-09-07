// SPDX-License-Identifier: GPL-3.0-or-later
#ifndef BACKENDS_EMSCRIPTEN_RETROM_HOST_H
#define BACKENDS_EMSCRIPTEN_RETROM_HOST_H
namespace RetromHost {
void poll();
void engineStarted();
void engineStopping();
void engineStopped(int error);
void saveOpened();
void saveClosed();
void saveRemoved();
}
#endif
