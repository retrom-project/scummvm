// SPDX-License-Identifier: GPL-3.0-or-later
#if defined(EMSCRIPTEN) && defined(RETROM_HOST)
#define FORBIDDEN_SYMBOL_EXCEPTION_FILE
#include "backends/fs/emscripten/retrom-fs.h"
#include "backends/fs/emscripten/emscripten-posix-fs.h"
#include "common/formats/json.h"
#include "common/stream.h"
#include <emscripten.h>

// -1 denotes a directory; -2 denotes a missing entry. File sizes stay 64-bit.
EM_JS(double, retromFileSize, (const char *path), {
	return Module.retromHost.files.stat(UTF8ToString(path));
});

EM_JS(char *, retromDirectory, (const char *path), {
	return stringToNewUTF8(JSON.stringify(Module.retromHost.files.list(UTF8ToString(path))));
});

EM_ASYNC_JS(int, retromRead, (const char *path, double position, uint8 *buffer, uint32 length), {
	try {
		const bytes = await Module.retromHost.files.read(UTF8ToString(path), position, length);
		if (bytes.byteLength !== length) return -1;
		HEAPU8.set(bytes, buffer);
		return length;
	} catch (error) {
		Module.retromHost.failure(error);
		return -1;
	}
});

namespace {
class RetromReadStream : public Common::SeekableReadStream {
	Common::String _path;
	int64 _size;
	int64 _position = 0;
	bool _error = false;
	bool _eos = false;
public:
	RetromReadStream(const Common::String &path, int64 size) : _path(path), _size(size) {}
	bool err() const override { return _error; }
	void clearErr() override { _error = _eos = false; }
	bool eos() const override { return _eos; }
	int64 pos() const override { return _position; }
	int64 size() const override { return _size; }
	bool seek(int64 offset, int whence = SEEK_SET) override {
		int64 base = whence == SEEK_SET ? 0 : whence == SEEK_CUR ? _position : _size;
		if ((whence != SEEK_SET && whence != SEEK_CUR && whence != SEEK_END) ||
			(offset < 0 && offset < -base) || (offset > 0 && offset > _size - base))
			return false;
		_position = base + offset;
		_eos = false;
		return true;
	}
	uint32 read(void *data, uint32 length) override {
		uint32 available = (uint32)MIN<int64>(_size - _position, length);
		_eos = available < length;
		uint32 copied = 0;
		while (copied < available) {
			// Even engines requesting an entire archive cannot create an unbounded HTTP request.
			uint32 block = MIN<uint32>(available - copied, 256 * 1024);
			if (retromRead(_path.c_str(), (double)_position, (uint8 *)data + copied, block) != (int)block) {
				_error = true;
				break;
			}
			copied += block;
			_position += block;
		}
		return copied;
	}
};
} // namespace

RetromFilesystemNode::RetromFilesystemNode(const Common::String &path) : _path(path) {
	while (_path.size() > 5 && _path.lastChar() == '/')
		_path.deleteLastChar();
	_size = (int64)retromFileSize(_path.c_str());
}

Common::String RetromFilesystemNode::getName() const {
	const char *separator = strrchr(_path.c_str(), '/');
	return separator ? separator + 1 : _path.c_str();
}

AbstractFSNode *RetromFilesystemNode::getChild(const Common::String &name) const {
	if (!isDirectory() || name.empty() || name.contains('/') || name == "." || name == "..")
		return nullptr;
	return new RetromFilesystemNode(_path + "/" + name);
}

bool RetromFilesystemNode::getChildren(AbstractFSList &list, ListMode mode, bool hidden) const {
	if (!isDirectory())
		return false;
	char *raw = retromDirectory(_path.c_str());
	Common::JSONValue *children = Common::JSON::parse(raw);
	free(raw);
	if (!children || !children->isArray()) {
		delete children;
		return false;
	}
	for (auto *child : children->asArray()) {
		const Common::String &name = child->asString();
		AbstractFSNode *node = getChild(name);
		if (!node)
			continue;
		if ((!hidden && name.hasPrefix(".")) || (mode == Common::FSNode::kListFilesOnly && node->isDirectory()) ||
			(mode == Common::FSNode::kListDirectoriesOnly && !node->isDirectory()))
			delete node;
		else
			list.push_back(node);
	}
	delete children;
	return true;
}

AbstractFSNode *RetromFilesystemNode::getParent() const {
	if (_path == "/game" || _path == "/data")
		return new EmscriptenPOSIXFilesystemNode("/");
	return new RetromFilesystemNode(Common::String(_path.c_str(), strrchr(_path.c_str(), '/')));
}

Common::SeekableReadStream *RetromFilesystemNode::createReadStream() {
	return _size < 0 ? nullptr : new RetromReadStream(_path, _size);
}
#endif
