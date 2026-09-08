// SPDX-License-Identifier: GPL-3.0-or-later
#ifndef BACKENDS_FS_EMSCRIPTEN_RETROM_FS_H
#define BACKENDS_FS_EMSCRIPTEN_RETROM_FS_H

#include "backends/fs/abstract-fs.h"

class RetromFilesystemNode : public AbstractFSNode {
	Common::String _path;
	int64 _size;
public:
	explicit RetromFilesystemNode(const Common::String &path);
	bool exists() const override { return _size >= -1; }
	Common::U32String getDisplayName() const override { return getName(); }
	Common::String getName() const override;
	Common::String getPath() const override { return _path; }
	bool isDirectory() const override { return _size == -1; }
	bool isReadable() const override { return exists(); }
	bool isWritable() const override { return false; }
	AbstractFSNode *getChild(const Common::String &name) const override;
	bool getChildren(AbstractFSList &list, ListMode mode, bool hidden) const override;
	AbstractFSNode *getParent() const override;
	Common::SeekableReadStream *createReadStream() override;
	Common::SeekableWriteStream *createWriteStream(bool atomic) override { return nullptr; }
	bool createDirectory() override { return false; }
};

#endif
