// SPDX-License-Identifier: GPL-3.0-or-later
#ifndef BASE_RETROM_DETECTION_H
#define BASE_RETROM_DETECTION_H

#include "common/path.h"

namespace Base {
// A bounded transport for the upstream detector; contains no game signatures.
bool printRetromDetection(const Common::Path &path, bool recursive);
void deferRetromDetectionOutput();
const Common::String &retromDetectionOutput();
}

#endif
