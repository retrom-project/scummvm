// SPDX-License-Identifier: GPL-3.0-or-later
#ifndef COMMON_RETROM_RESTORE_H
#define COMMON_RETROM_RESTORE_H

namespace RetromHost {
#if defined(EMSCRIPTEN) && defined(RETROM_HOST)
// Report actual deserialization, not the request to load or the first frame.
void restoreResult(int slot, bool success);
#else
inline void restoreResult(int, bool) {}
#endif
}

#endif
