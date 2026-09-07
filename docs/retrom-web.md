# Retrom hosted Web backend

The fork is maintained at `https://github.com/retrom-project/scummvm`, based on
`v2026.3.0` (`fed42f2068dcafc6aafa1c28c77e4c88def74b66`). `master` mirrors upstream;
Retrom changes belong on `retrom/2026.3.0` and its feature branches. The ABI is
`scummvm-host-v1`; the authoritative toolchain, codec inputs and engine selection
are in `.github/rpg-runtime/build-lock.json` and `retrom-fork.json`.

## Building

Run `.github/rpg-runtime/build-candidate.sh /absolute/empty/output` as the current
non-root user, or use the consuming workspace's explicit PFB core-build command.
The script pins the SDK image, verifies downloaded codec sources, builds the
static Linux x86-64 detector and the hosted Web backend, runs detector/JavaScript
regressions, and emits `scummvm-runtime.zip` plus a candidate descriptor containing
actual Git and working-tree identity. No tag or Release is created by this command.

The archive contains the ES module factory, shared WASM, 105 selected stable engine
plugins, support data, the native detector, a closed manifest of file sizes and
SHA-256 digests, and upstream/codec licenses. Engine plugins use Emscripten side
modules and share the main module's exact SDK/ABI; they are not interchangeable
across builds. The runtime installs only the selected plugin into `/plugins`.
Detection remains complete and independent of executable plugin availability.

Incremental build state lives in ignored `.retrom/`. `build-web.sh` exports its
Emscripten cache inside the SDK shell because the SDK entrypoint replaces an
inherited `EM_CACHE`. Changes to configure/link flags may rebuild every engine.
Runtime aggregation consumes this archive; it never compiles ScummVM.

## Host contract

`scummvm-retrom.mjs` exports the ABI and `createScummVM`. The host supplies an SDL
canvas, `noInitialRun`, verified WASM bytes, immutable asset resolution and
`retromHost`, creates fresh `/saves`, `/plugins` and configuration in MEMFS, imports
an explicitly selected save before `callMain`, then launches the explicit target.
There is no hosted launcher, `--auto-detect` selection, IDBFS or implicit previous
session recovery. The native detector's bounded JSON protocol is documented in
[retrom-detector.md](retrom-detector.md).

The read-only `/game` and `/data` filesystem forwards stat/list/read to the host.
Reads yield through Asyncify, preserve 64-bit offsets, request at most 256 KiB,
and copy returned bytes only after reacquiring the WASM heap. Missing, short or
failed reads fail explicitly. The browser adapter owns persistent block caching.

At event boundaries the host may request native capture or quit and pause/resume
through a native pause token. Capture requires runtime saving and native save-list
support, checks the current scene, allocates a free non-autosave slot, and waits
for the slot to appear with no open save streams. Deferred engine saves use the
same completion boundary with a 15-second limit. Existing slots are not overwritten.
The result reports the precise native slot; unsupported games retain in-game
saving. Startup restoration follows the engine's native load-at-startup support;
no latest-slot guessing or execution-memory snapshot is introduced.

Save stream open/close and successful file deletion notify the host. The browser
copies a complete file set at safe boundaries, computes content revisions and
bundles all companion files. Engine termination has two phases:
`onEngineStopping` closes live controls and captures the last screenshot before
backend teardown; `onEngineStopped` follows engine destruction so the final bundle
includes destructor writes. The host receives one final save handoff and one exit
event. Requested exits use the same cleanup boundary without reopening the launcher.

## Verification and publishing

`test_detector.py` exercises bounded detection and supports an optional local
public-game corpus. `test_web_javascript.py` executes the embedded speech/MIDI
JavaScript under strict parsing. Hosted control, file-cache and native-save tests
belong to the consuming runtime; product import, review, launch, input and restore
acceptance belongs to Retrom. Building this fork alone does not prove game support.

Before publishing a tag matching `retrom-fork.json`, complete those product cases,
record the exact core bytes and engine/plugin selection, and publish the archive
and release descriptor from the maintenance branch. Candidate working-tree identity
must not be presented as a released tag. Distribution must retain the archive's
license notices and provide the corresponding fork source and build inputs.
