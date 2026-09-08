#!/usr/bin/env python3
"""Validate the closed ScummVM archive and describe the exact fork release bytes."""
import argparse
import hashlib
import json
import re
import stat
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAX_ARCHIVE = 256 * 1024 * 1024
MAX_UNPACKED = 768 * 1024 * 1024


def validate_archive(path, fork, lock):
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= MAX_ARCHIVE:
        raise ValueError("SCUMMVM_RELEASE_ARCHIVE_INVALID")
    engines = {e['id']: f"plugins/lib{e['id']}.so" for e in lock['engines']
               if e['enabled'] and e['parent'] == e['id']}
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = [e.filename for e in entries]
        if (not engines or len(entries) > 4096 or len(set(names)) != len(names)
                or sum(e.file_size for e in entries) > MAX_UNPACKED):
            raise ValueError("SCUMMVM_RELEASE_ARCHIVE_INVALID")
        for entry in entries:
            pieces = entry.filename.split('/')
            mode = entry.external_attr >> 16
            if (any(p in ('', '.', '..') for p in pieces) or '\\' in entry.filename
                    or any(ord(c) < 32 or ord(c) == 127 for c in entry.filename)
                    or not stat.S_ISREG(mode) or entry.flag_bits & 1
                    or not 0 < entry.file_size <= 128 * 1024 * 1024):
                raise ValueError("SCUMMVM_RELEASE_ARCHIVE_INVALID")
        if 'manifest.json' not in names or archive.getinfo('manifest.json').file_size > 1024 * 1024:
            raise ValueError("SCUMMVM_RELEASE_MANIFEST_INVALID")
        manifest = json.loads(archive.read('manifest.json'))
        if (set(manifest) != {'schemaVersion', 'adapterAbi', 'upstreamCommit', 'engines', 'files'}
                or manifest['schemaVersion'] != 1 or manifest['adapterAbi'] != fork['adapterAbi']
                or manifest['upstreamCommit'] != lock['upstreamCommit'] or manifest['engines'] != engines
                or not isinstance(manifest['files'], list)):
            raise ValueError("SCUMMVM_RELEASE_MANIFEST_INVALID")
        records = manifest['files']
        record_names = [r['path'] for r in records]
        required = {'scummvm.mjs', 'scummvm-retrom.mjs', 'scummvm.wasm',
                    'native/linux-x86_64/scummvm-detector', 'licenses/COPYING',
                    'licenses/SDL3-LICENSE.txt', 'licenses/build-inputs.json', *engines.values()}
        if (len(set(record_names)) != len(records) or set(names) != {*record_names, 'manifest.json'}
                or not required.issubset(record_names)
                or {n for n in names if n.startswith('plugins/')} != set(engines.values())):
            raise ValueError("SCUMMVM_RELEASE_FILE_SET_INVALID")
        for record in records:
            if set(record) != {'path', 'sizeBytes', 'sha256'}:
                raise ValueError("SCUMMVM_RELEASE_MANIFEST_INVALID")
            data = archive.read(record['path'])
            if len(data) != record['sizeBytes'] or hashlib.sha256(data).hexdigest() != record['sha256']:
                raise ValueError("SCUMMVM_RELEASE_DIGEST_INVALID")
            if record['path'].endswith(('.wasm', '.so')) and data[:8] != b'\0asm\1\0\0\0':
                raise ValueError("SCUMMVM_RELEASE_WASM_INVALID")
        if json.loads(archive.read('licenses/build-inputs.json')) != lock:
            raise ValueError("SCUMMVM_RELEASE_SOURCE_INVALID")
    return {'filename': path.name, 'sizeBytes': path.stat().st_size,
            'observedSha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def describe(output, repository, tag, commit):
    fork = json.loads((ROOT / 'retrom-fork.json').read_text())
    lock = json.loads((ROOT / '.github/rpg-runtime/build-lock.json').read_text())
    if (repository != fork['forkRepository'] or not re.fullmatch(fork['releaseTagPattern'], tag)
            or not re.fullmatch(r'[0-9a-f]{40}', commit)):
        raise ValueError('SCUMMVM_RELEASE_IDENTITY_INVALID')
    names = {p.name for p in output.iterdir()} - {'rpg-runtime-release.json'}
    if names != {'scummvm-runtime.zip'}:
        raise ValueError('SCUMMVM_RELEASE_FILE_SET_INVALID')
    asset = validate_archive(output / 'scummvm-runtime.zip', fork, lock)
    return {'schemaVersion': 1, 'repository': repository, 'tag': tag, 'commit': commit,
            'adapterAbi': fork['adapterAbi'], 'digestPolicy': 'OBSERVED_CACHE_INTEGRITY_ONLY',
            'sourceCommits': {source['role']: source['commit'] for source in fork['upstreams']},
            'assets': [asset]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--check-only', action='store_true')
    for key in ('repository', 'tag', 'commit'):
        parser.add_argument('--' + key)
    args = parser.parse_args()
    if args.check_only:
        validate_archive(args.output / 'scummvm-runtime.zip',
                         json.loads((ROOT / 'retrom-fork.json').read_text()),
                         json.loads((ROOT / '.github/rpg-runtime/build-lock.json').read_text()))
        print('ScummVM archive integrity: OK')
        raise SystemExit(0)
    if not all((args.repository, args.tag, args.commit)):
        parser.error('repository, tag and commit are required for release metadata')
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() != args.commit:
        raise ValueError('SCUMMVM_RELEASE_COMMIT_INVALID')
    metadata = describe(args.output, args.repository, args.tag, args.commit)
    (args.output / 'rpg-runtime-release.json').write_text(json.dumps(metadata, indent=2, sort_keys=True) + '\n')
