// SPDX-License-Identifier: GPL-3.0-or-later
import createScummVM from "./scummvm.mjs";

export const adapterAbi = "scummvm-host-v1";
export {createScummVM};
globalThis.__RETROM_SCUMMVM_MODULE_V1__ = {adapterAbi, createScummVM};
