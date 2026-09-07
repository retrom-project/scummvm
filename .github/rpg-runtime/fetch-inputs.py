#!/usr/bin/env python3
"""Reuse source archives only after checking the immutable build lock."""
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK = json.loads((ROOT / ".github/rpg-runtime/build-lock.json").read_text())
DESTINATION = ROOT / ".retrom/libs"
DESTINATION.mkdir(parents=True, exist_ok=True)


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


for item in LOCK["sources"]:
    target = DESTINATION / item["filename"]
    if target.is_file() and digest(target) == item["sha256"]:
        continue
    temporary = target.with_suffix(target.suffix + ".partial")
    request = urllib.request.Request(item["url"], headers={"User-Agent": "Retrom-ScummVM-build/1"})
    with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as output:
        size = 0
        while block := response.read(1024 * 1024):
            size += len(block)
            if size > 128 * 1024 * 1024:
                raise ValueError("source exceeds build input limit")
            output.write(block)
    if digest(temporary) != item["sha256"]:
        raise ValueError(f'source checksum mismatch: {item["filename"]}')
    temporary.replace(target)
