#!/usr/bin/env python3
"""Package only explicitly enabled engines and upstream-declared supporting data."""
import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def sources():
    lock = json.loads((ROOT / ".github/rpg-runtime/build-lock.json").read_text())
    engines = {e["id"]: f'plugins/lib{e["id"]}.so' for e in lock["engines"] if e["enabled"] and e["parent"] == e["id"]}
    built = {path.name for path in (ROOT / ".retrom/web/plugins").glob("*.so")}
    if not engines or built != {Path(path).name for path in engines.values()}:
        raise ValueError("built plugins differ from the explicit stable-engine lock")
    files = {"scummvm.mjs": ROOT / ".retrom/web/scummvm.mjs", "scummvm.wasm": ROOT / ".retrom/web/scummvm.wasm",
             "scummvm-retrom.mjs": ROOT / "dists/emscripten/scummvm-retrom.mjs",
             "native/linux-x86_64/scummvm-detector": ROOT / ".retrom/native/scummvm"}
    for path in engines.values():
        files[path] = ROOT / ".retrom/web" / path
    output = subprocess.check_output(["make", "--no-print-directory", "-s", "-f", "Makefile", "-f",
                                      "../../.github/rpg-runtime/package.mk", "retrom-dist-list"],
                                     cwd=ROOT / ".retrom/web", text=True)
    for line in output.splitlines():
        kind, relative = line.split("\t")
        source = (ROOT / ".retrom/web" / relative).resolve()
        target = f'data/{"shaders/" if kind == "shader" else ""}{source.name}'
        if target in files and digest(files[target]) != digest(source):
            raise ValueError(f"conflicting upstream data: {target}")
        files[target] = source
    for path in [ROOT / "COPYING", ROOT / "COPYRIGHT", ROOT / "AUTHORS", *sorted((ROOT / "LICENSES").glob("*"))]:
        if path.is_file():
            files[f"licenses/{path.name}"] = path
    files["licenses/build-inputs.json"] = ROOT / ".github/rpg-runtime/build-lock.json"
    for name, directory in [("libmad", "libmad-0.15.1b"), ("libtheora", "libtheora-1.1.1"),
                            ("libmpeg2", "libmpeg2-946bf4b518aacc224f845e73708f99e394744499")]:
        files[f"licenses/{name}-COPYING"] = ROOT / ".retrom/libs" / directory / "COPYING"
    return lock, engines, files


def stage(destination):
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("stage must be empty")
    destination.mkdir(parents=True, exist_ok=True)
    lock, engines, files = sources()
    records = []
    for relative, source in sorted(files.items()):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        records.append({"path": relative, "sizeBytes": target.stat().st_size, "sha256": digest(target)})
    manifest = {"schemaVersion": 1, "adapterAbi": "scummvm-host-v1", "upstreamCommit": lock["upstreamCommit"],
                "engines": engines, "files": records}
    (destination / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")


def archive(source, destination):
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            entry = zipfile.ZipInfo(path.relative_to(source).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            output.writestr(entry, path.read_bytes())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", type=Path)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    stage(args.stage)
    if args.archive:
        archive(args.stage, args.archive)
