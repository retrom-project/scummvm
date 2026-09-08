#!/usr/bin/env python3
"""Exercise release archive integrity without third-party game or binary fixtures."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('release', ROOT / '.github/rpg-runtime/verify-release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def archive(self, directory, mutate=None, extra=None):
        lock = {'upstreamCommit': 'a' * 40, 'engines': [{'id': 'sky', 'parent': 'sky', 'enabled': True}]}
        fork = {'adapterAbi': 'scummvm-host-v1'}
        files = {'scummvm.mjs': b'// owned fixture', 'scummvm-retrom.mjs': b'// owned fixture',
                 'scummvm.wasm': b'\0asm\1\0\0\0', 'plugins/libsky.so': b'\0asm\1\0\0\0',
                 'native/linux-x86_64/scummvm-detector': b'owned detector placeholder',
                 'licenses/COPYING': b'owned fixture', 'licenses/SDL3-LICENSE.txt': b'owned fixture',
                 'licenses/build-inputs.json': json.dumps(lock).encode()}
        manifest = {'schemaVersion': 1, 'adapterAbi': fork['adapterAbi'], 'upstreamCommit': lock['upstreamCommit'],
                    'engines': {'sky': 'plugins/libsky.so'}, 'files': [
                        {'path': name, 'sizeBytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                        for name, data in sorted(files.items())]}
        if mutate:
            mutate(files, manifest)
        files['manifest.json'] = json.dumps(manifest).encode()
        path = Path(directory) / 'scummvm-runtime.zip'
        with zipfile.ZipFile(path, 'w') as output:
            for name, data in [*files.items(), *(extra or [])]:
                entry = zipfile.ZipInfo(name)
                entry.external_attr = 0o100644 << 16
                output.writestr(entry, data)
        return path, fork, lock

    def test_valid_closed_archive_has_exact_observed_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            path, fork, lock = self.archive(directory)
            result = release.validate_archive(path, fork, lock)
            self.assertEqual(result['observedSha256'], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(result['sizeBytes'], path.stat().st_size)

    def test_rejects_changed_content_missing_plugin_wrong_engine_and_extra_entries(self):
        cases = [
            (lambda f, m: f.update({'scummvm.mjs': b'changed'}), None),
            (lambda f, m: f.pop('plugins/libsky.so'), None),
            (lambda f, m: m.update({'engines': {'scumm': 'plugins/libscumm.so'}}), None),
            (None, [('unlisted.txt', b'owned fixture')]),
            (None, [('../outside', b'owned fixture')]),
            (None, [('licenses/COPYING', b'duplicate')]),
        ]
        for mutate, extra in cases:
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as directory:
                path, fork, lock = self.archive(directory, mutate, extra)
                with self.assertRaises(ValueError):
                    release.validate_archive(path, fork, lock)

    def test_rejects_archive_symlink_and_wrong_release_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            path, fork, lock = self.archive(directory)
            link = path.with_name('linked.zip'); link.symlink_to(path)
            with self.assertRaises(ValueError):
                release.validate_archive(link, fork, lock)
            for repository, tag, commit in [
                ('https://example.org/scummvm', 'retrom-core-2026.3.0-r1', 'a' * 40),
                ('https://github.com/retrom-project/scummvm', 'v2026.3.0', 'a' * 40),
                ('https://github.com/retrom-project/scummvm', 'retrom-core-2026.3.0-r1', 'master'),
            ]:
                with self.assertRaisesRegex(ValueError, 'IDENTITY_INVALID'):
                    release.describe(Path(directory), repository, tag, commit)


if __name__ == '__main__':
    unittest.main()
