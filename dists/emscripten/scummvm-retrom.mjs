// SPDX-License-Identifier: GPL-3.0-or-later
import createModule from "./scummvm.mjs";

export const adapterAbi = "scummvm-host-v1";
export function createScummVM(options) {
  const canvas = options.canvas;
  const getContext = canvas.getContext;
  // Native pause can outlive a browser paint. Keep that frame readable by toBlob.
  // Apply this only to the host's canvas, including contexts created by callMain.
  canvas.getContext = function (type, attributes) {
    return getContext.call(this, type,
      ["webgl", "webgl2", "experimental-webgl"].includes(type)
        ? {...attributes, preserveDrawingBuffer: true} : attributes);
  };
  return createModule(options);
}
globalThis.__RETROM_SCUMMVM_MODULE_V1__ = {adapterAbi, createScummVM};
