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
and native restore/input regressions, and emits `scummvm-runtime.zip` plus a candidate descriptor containing
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

The pinned SDL 3.2.4 browser driver needs one bounded local patch: initialize axes
from the first browser sample even when its timestamp is unchanged. Without it,
SDL discards the first stick movement as an initial position. `prepare-sdl3.py`
checks the SDK version and exact original source hash, applies the marked patch
idempotently, and invalidates only this worktree's SDL libraries and final link.
Unknown source fails the build. `test_sdl3_axes.py` executes the actual SDL sampling
and event delivery functions for first movement, release and a fresh device. The
archive retains SDL's original license. The left stick moves ScummVM's virtual
mouse; D-pad actions remain engine-specific upstream mappings.

SDL3 device-added events contain instance IDs, whereas `joystick_num` selects an
ordinal in `SDL_GetJoysticks`. The event source resolves that ordinal before
opening a newly discovered controller, keeps an already open controller intact,
and accepts a fresh instance after disconnection. This covers browsers exposing
a controller only after gameplay begins. `test_sdl3_hotplug.py` executes the real
handlers for late discovery, reconnection, unrelated devices, disabled/invalid
selection, duplicate startup events and open failure, for gamepads and joysticks.

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
Hosted OpenGL drawing reads the current canvas backing dimensions before rendering,
including when a browser resize arrives during an Asyncify yield ahead of SDL's
resize event. Pausing stops engine simulation while retaining presentation updates,
so resizing a paused game redraws its existing surface at the new dimensions.
The factory preserves the supplied canvas's WebGL drawing buffer so screenshots
remain readable after browser presentation, including while paused; other canvases
and non-WebGL contexts are unaffected.
The result reports the precise native slot; unsupported games retain in-game
saving. Startup restoration requires both native load-at-startup support and an explicit
`onRestoreResult(slot, success)` observation after actual deserialization. Sky,
SCUMM, SCI, Queen and Drascula provide that observation in this build. Other engines
retain in-game restoration until an equivalent completion boundary is integrated.
The host waits for the exact restored slot before completing mount and fails on
rejection or timeout; a failed observed load requests native quit. Drascula reports
a chapter change only after the eventual load succeeds, not when it schedules the
chapter transition. No latest-slot guessing or execution-memory snapshot is used.

Save stream open/close and successful file deletion notify the host. The browser
copies a complete file set at safe boundaries, computes content revisions and
bundles all companion files. Engine termination has two phases:
`onEngineStopping` closes live controls and captures the last screenshot before
backend teardown; `onEngineStopped` follows engine destruction so the final bundle
includes destructor writes. The host receives one final save handoff and one exit
event. Requested exits use the same cleanup boundary without reopening the launcher.

## Verification and publishing

`test_detector.py` exercises bounded detection and supports an optional local
public-game corpus. `test_restore_boundary.py` executes the native exact-slot/once-only result guard.
`test_web_javascript.py` executes the embedded speech/MIDI
JavaScript under strict parsing and checks hosted WebGL buffer retention.
`test_canvas_resize.py` executes the native drawing and pause boundaries against
delayed resize delivery, repeated dimensions, unavailable/zero-size canvases and
resizing without resuming simulation. Hosted control, file-cache and native-save tests
belong to the consuming runtime; product import, review, launch, input and restore
acceptance belongs to Retrom. Building this fork alone does not prove game support.

Before publishing a tag matching `retrom-fork.json`, complete those product cases,
record the exact core bytes and engine/plugin selection, and publish the archive
and release descriptor from the maintenance branch. Candidate working-tree identity
must not be presented as a released tag. Distribution must retain the archive's
license notices and provide the corresponding fork source and build inputs.

## Maintained releases

The fork's default branch is `retrom/2026.3.0`; `master` remains an upstream
mirror. Integration PRs target the maintenance branch. The upstream CI stays on
the mirror while `retrom-quality.yml` builds and tests the complete Retrom native
and browser archive on maintenance PRs. Both CI and candidate builds use
`.github/rpg-runtime/build-assets.sh`, including detector, JavaScript, restore,
canvas resize, controller discovery and archive integrity checks.

After an approved maintenance PR is merged, publish a new annotated
`retrom-core-2026.3.0-rN` tag at that commit. Never move or reuse a released tag.
`retrom-release.yml` verifies the tag object, commit, upstream ancestry and
maintenance ancestry, rebuilds and checks the same complete archive, then
publishes `scummvm-runtime.zip` and `rpg-runtime-release.json`. Metadata records
the exact fork commit, upstream source commit, ABI and observed archive digest
and size. Runtime aggregation must verify these fixed identities before using
the enclosed manifest, engine plugins, support data and Linux x86-64 detector.
