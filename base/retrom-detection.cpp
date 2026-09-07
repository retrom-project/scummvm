// SPDX-License-Identifier: GPL-3.0-or-later
#define FORBIDDEN_SYMBOL_EXCEPTION_printf

#include "base/retrom-detection.h"
#include "base/plugins.h"
#include "common/formats/json.h"
#include "common/fs.h"
#include "engines/game.h"
#include "engines/metaengine.h"

namespace Base {
namespace {

bool deferredOutput = false;
Common::String output;

Common::JSONValue *candidateJSON(const DetectedGame &game, const Common::String &root) {
	Common::JSONObject result;
	result["root"] = new Common::JSONValue(root);
	result["engineId"] = new Common::JSONValue(game.engineId);
	result["gameId"] = new Common::JSONValue(game.gameId);
	result["description"] = new Common::JSONValue(game.description);
	result["preferredTarget"] = new Common::JSONValue(game.preferredTarget);
	const char *language = Common::getLanguageCode(game.language);
	const char *platform = Common::getPlatformCode(game.platform);
	result["language"] = new Common::JSONValue(language ? language : "");
	result["platform"] = new Common::JSONValue(platform ? platform : "");
	result["extra"] = new Common::JSONValue(game.extra);
	result["guiOptions"] = new Common::JSONValue(game.getGUIOptions());
	result["canBeAdded"] = new Common::JSONValue(game.canBeAdded);
	result["isAddOn"] = new Common::JSONValue(game.isAddOn);
	result["hasUnknownFiles"] = new Common::JSONValue(game.hasUnknownFiles);
	result["supportLevel"] = new Common::JSONValue((long long)game.gameSupportLevel);
	Common::JSONObject config;
	for (const auto &entry : game._extraConfigEntries)
		config[entry._key] = new Common::JSONValue(entry._value);
	result["config"] = new Common::JSONValue(config);
	return new Common::JSONValue(result);
}

const char *scan(const Common::FSNode &directory, const Common::String &root, bool recursive,
		uint depth, uint &visited, Common::JSONArray &candidates) {
	if (depth > 32 || ++visited > 16384)
		return "SCUMMVM_DETECTION_LIMIT_EXCEEDED";
	Common::FSList files;
	if (!directory.exists() || !directory.isDirectory() || !directory.getChildren(files, Common::FSNode::kListAll))
		return "SCUMMVM_DETECTION_PATH_INVALID";
	// EngineManager expects a nonempty file list when assigning each detected path.
	if (!files.empty()) {
		const DetectedGames games = EngineMan.detectGames(files).listDetectedGames();
		for (const auto &game : games) {
			if (candidates.size() >= 4096)
				return "SCUMMVM_DETECTION_LIMIT_EXCEEDED";
			candidates.push_back(candidateJSON(game, root));
		}
	}
	if (recursive) {
		for (const auto &file : files) {
			if (!file.isDirectory())
				continue;
			Common::String relative = root.empty() ? file.getName() : root + "/" + file.getName();
			const char *error = scan(file, relative, true, depth + 1, visited, candidates);
			if (error)
				return error;
		}
	}
	return nullptr;
}

} // namespace

bool printRetromDetection(const Common::Path &path, bool recursive) {
	Common::JSONArray candidates;
	uint visited = 0;
	const char *error = path.empty() ? "SCUMMVM_DETECTION_PATH_INVALID" :
		scan(Common::FSNode(path), "", recursive, 0, visited, candidates);
	if (error) {
		for (auto *candidate : candidates)
			delete candidate;
		candidates.clear();
	}
	Common::JSONObject result;
	result["schemaVersion"] = new Common::JSONValue(1LL);
	result["upstreamCommit"] = new Common::JSONValue("fed42f2068dcafc6aafa1c28c77e4c88def74b66");
	result["error"] = error ? new Common::JSONValue(error) : new Common::JSONValue();
	result["candidates"] = new Common::JSONValue(candidates);
	Common::JSONValue document(result);
	output = document.stringify() + "\n";
	if (!deferredOutput)
		printf("%s", output.c_str());
	return error == nullptr;
}

void deferRetromDetectionOutput() {
	deferredOutput = true;
}

const Common::String &retromDetectionOutput() {
	return output;
}

} // namespace Base
