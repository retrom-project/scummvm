# Retrom native detection protocol

The Retrom fork starts at upstream `v2026.3.0`, commit
`fed42f2068dcafc6aafa1c28c77e4c88def74b66`. `master` remains an upstream
mirror; development branches start at the local `retrom/2026.3.0` baseline.
The fork is <https://github.com/retrom-project/scummvm>.

Build the native command with `.github/rpg-runtime/build-native.sh`.
It uses the null backend, all upstream detection tables, and the SCI and
Wintermute execution components required by their external fallback detectors.
Other execution engines are unnecessary for server detection. The command does
not start a game or modify a game directory.

```
scummvm --config=/dev/null --retrom-detect --recursive --path=/materialized/input
```

On Linux, stdout is exclusively a JSON document; upstream diagnostics go to
stderr, including diagnostics printed directly by detectors. Exit zero means
the scan completed, including a successful scan with zero candidates. Nonzero
means failure: never consume its candidates. The upstream argument parser can
reject an invocation before JSON is generated (for example a nonexistent
`--path`). The caller must inspect the exit status before parsing stdout.

The document has `schemaVersion: 1`, `upstreamCommit`, `error` (null or a stable
code), and `candidates`. Each candidate preserves:

- `root`: directory relative to the input root; the input root itself is `""`.
- `engineId`, `gameId`, `description`, `preferredTarget`.
- `language`, `platform`, `extra`, `guiOptions`, and the upstream extra `config` map.
- `canBeAdded`, `isAddOn`, `hasUnknownFiles`, and numeric upstream `supportLevel`.

The transport does not rank candidates, remove unknown variants, infer game
identity, choose a first match, or derive filename signatures. Detection is
`EngineMan.detectGames(...).listDetectedGames()`. A host must retain all variants
and bind selection to the immutable input snapshot. Executable engine admission
is a separate check against the actual Web build's engine manifest.

Recursion is bounded to 32 levels, 16,384 directories and 4,096 candidates.
Exceeding a limit fails the whole scan and discards partial results. The host
must additionally materialize a symlink-free input tree from its validated
content index, bound file counts and bytes, apply a subprocess timeout and
stdout/stderr limits, and validate every returned root against that tree.
The CLI is not an untrusted-filesystem sandbox.

Run the transport regression suite after building:

```
python3 .github/rpg-runtime/test_detector.py
SCUMMVM_TEST_GAMES=/path/to/extracted-public-games python3 .github/rpg-runtime/test_detector.py
```

The optional public-game case exercises the actual upstream detectors for
Beneath a Steel Sky, Flight of the Amazon Queen, and Drascula. Game archives and
extracted content remain outside source control. Absence of these optional
samples is reported as a skipped test, never as proof of game compatibility.
