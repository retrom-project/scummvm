// SPDX-License-Identifier: GPL-3.0-or-later
#if defined(EMSCRIPTEN) && defined(RETROM_HOST)
#define FORBIDDEN_SYMBOL_EXCEPTION_FILE
#include "backends/platform/sdl/emscripten/retrom-host.h"
#include "common/config-manager.h"
#include "common/system.h"
#include "engines/engine.h"
#include "engines/metaengine.h"
#include <emscripten.h>

EM_JS(void, retromStatus, (int capture, int available, int automatic), {
	Module.retromHost.onStatus({capture: !!capture, available: !!available, automatic: !!automatic});
});
EM_JS(int, retromCommand, (), { const value = Module.retromHost.command; Module.retromHost.command = 0; return value; });
EM_JS(bool, retromShouldPause, (), { return Module.retromHost.paused && !Module.retromHost.command; });
EM_JS(void, retromPaused, (int paused), { Module.retromHost.onPaused(!!paused); });
EM_JS(void, retromSaveResult, (int slot, int error), { Module.retromHost.onSaveResult(slot, error); });
EM_JS(void, retromRestoreResult, (int slot, int success), { Module.retromHost.onRestoreResult(slot, !!success); });
EM_JS(void, retromWriteEvent, (int open), { Module.retromHost.onWrite(!!open); });
EM_JS(void, retromStopping, (), { Module.retromHost.onEngineStopping(); });
EM_JS(void, retromStopped, (int error), { Module.retromHost.onEngineStopped(error); });
EM_JS(void, retromBoundary, (), { Module.retromHost.onBoundary(); });

namespace RetromHost {
namespace {
bool running = false;
bool polling = false;
int pendingSlot = -1;
uint32 saveDeadline = 0;
uint openSaves = 0;
bool restoreReported = false;

bool hasRestoreResult() {
	const Common::String id = ConfMan.get("engineid");
	return id == "sky" || id == "queen" || id == "scumm" || id == "sci" || id == "drascula";
}

int unusedSlot(const MetaEngine &meta) {
	const SaveStateList saves = meta.listSaves(ConfMan.getActiveDomainName().c_str(), true);
	for (int slot = 1; slot <= MIN(meta.getMaximumSaveSlot(), 9999); ++slot) {
		if (slot == meta.getAutosaveSlot())
			continue;
		bool occupied = false;
		for (const auto &save : saves)
			occupied |= save.getSaveSlot() == slot;
		if (!occupied)
			return slot;
	}
	return -1;
}

void saveAtBoundary(const MetaEngine &meta, bool available) {
	int slot = available ? unusedSlot(meta) : -1;
	if (slot < 0) {
		retromSaveResult(-1, Common::kWritePermissionDenied);
		return;
	}
	pendingSlot = slot;
	saveDeadline = g_system->getMillis() + 15000;
	Common::Error result = g_engine->saveGameState(slot, "Retrom checkpoint", false);
	if (result.getCode() != Common::kNoError) {
		pendingSlot = -1;
		retromSaveResult(-1, result.getCode());
	}
}

void finishSave(const MetaEngine &meta) {
	if (pendingSlot < 0 || openSaves)
		return;
	const SaveStateList saves = meta.listSaves(ConfMan.getActiveDomainName().c_str());
	for (const auto &save : saves) {
		if (save.getSaveSlot() == pendingSlot) {
			int slot = pendingSlot;
			pendingSlot = -1;
			retromSaveResult(slot, 0);
			return;
		}
	}
	if ((int32)(g_system->getMillis() - saveDeadline) >= 0) {
		pendingSlot = -1;
		retromSaveResult(-1, Common::kWritingFailed);
	}
}
} // namespace

void poll() {
	if (!running || !g_engine || polling)
		return;
	polling = true;
	const MetaEngine &meta = *g_engine->getMetaEngine();
	bool capture = g_engine->hasFeature(Engine::kSupportsSavingDuringRuntime) && meta.hasFeature(MetaEngine::kSupportsListSaves);
	bool available = capture && g_engine->canSaveGameStateCurrently();
	finishSave(meta);
	retromStatus(capture, available && pendingSlot < 0, hasRestoreResult() && meta.hasFeature(MetaEngine::kSupportsLoadingDuringStartup));
	const int command = retromCommand();
	if (command == 1 && pendingSlot < 0)
		saveAtBoundary(meta, available);
	else if (command == 2)
		Engine::quitGame();
	if (!openSaves && pendingSlot < 0)
		retromBoundary();
	if (pendingSlot < 0 && retromShouldPause()) {
		PauseToken pause = g_engine->pauseEngine();
		// Pause simulation, but keep the retained game surface fitted to the canvas.
		// A resize may arrive before pausing or during any browser yield below.
		g_system->updateScreen();
		retromPaused(1);
		while (retromShouldPause()) {
			g_system->updateScreen();
			if (!openSaves)
				retromBoundary();
			emscripten_sleep(16);
		}
		pause.clear();
		retromPaused(0);
	}
	polling = false;
}

void engineStarted() { running = true; restoreReported = false; }
void restoreResult(int slot, bool success) {
	if (restoreReported || !ConfMan.hasKey("save_slot") || ConfMan.getInt("save_slot") != slot)
		return;
	restoreReported = true;
	retromRestoreResult(slot, success);
	if (!success)
		Engine::quitGame();
}
void engineStopping() {
	running = false;
	if (pendingSlot >= 0) {
		pendingSlot = -1;
		retromSaveResult(-1, Common::kWritingFailed);
	}
	retromStopping();
}
void engineStopped(int error) { retromStopped(error); }
void saveOpened() { ++openSaves; retromWriteEvent(1); }
void saveClosed() { --openSaves; retromWriteEvent(0); }
void saveRemoved() { retromWriteEvent(1); retromWriteEvent(0); }
} // namespace RetromHost
#endif
