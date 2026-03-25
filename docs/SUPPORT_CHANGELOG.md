# SUPPORT_CHANGELOG - MAS-004_VJ6530-ZBC-Bridge

## 2026-03-25 (Bridge Sessions Negotiate `HCV`)
- `ZbcBridgeClient` now tries `HCV` once per opened client session before running bridge operations.
- Goal: align bridge-side ad-hoc sessions with the live 6530 expectation that each fresh TCP session should negotiate host capabilities up front.

## 2026-03-25 (Async Profile Export Shim)
- `_zbc_library.py` now also re-exports `VJ6530_TCP_NO_CRC_PROFILE` so the Databridge async layer can reuse the verified long-lived 6530 transport profile without duplicating bridge-internal import logic.

## 2026-03-25 (Standalone Ownership Clarification)
- The standalone `mas004-vj6530-zbc-bridge.service` is now documented as a diagnostic/probe daemon, not a second live owner of `3002` when `MAS-004_RPI-Databridge` already operates the 6530 path.
- TEST runtime keeps this service disabled so it does not compete with the Databridge async/poll session handling.

## 2026-03-25 (`PRINTER_STATE_CODE` Bridge Support)
- `ZbcBridgeClient` now exposes numeric `STATUS[PRINTER_STATE_CODE]` reads.
- `write_mapped_value()` now accepts `STATUS[PRINTER_STATE_CODE]` and forwards the directly commandable states `0`, `3`, `6` to the shared library control path.
- The bridge status snapshot now tracks the numeric code so upper layers can acknowledge `TTS0001` writes consistently.
- Refined live transition handling:
  - `3` from `6` is now realized as `STARTUP` then `START`
  - `0` from `6` is realized as `STARTUP`
  - derived targets `1`, `2`, `4`, `5` stay rejected instead of pretending to be commandable

## 2026-03-25 (Standalone Probe Calm-Down)
- `ZbcBridgeClient.probe()` now uses the bridge-level summary cache instead of forcing a fresh live summary request every time.
- The standalone `mas004-vj6530-zbc-bridge.service` now creates its probe client with a longer summary-cache window.
- A single timeout immediately after a recent successful probe is now treated as transient and logged without flipping the daemon into warning/down-state noise.

## 2026-03-25 (Probe Client Reuse)
- Service probe loop now reuses one `ZbcBridgeClient` as long as `host`, `port` and `timeout_s` stay unchanged.
- `ZbcBridgeClient.probe()` now reuses an already-known transport profile instead of forcing a fresh profile-detect on every probe call.
- Goal: reduce repeated 6530 profile handshakes and avoid avoidable probe load on the shared `3002` ZBC endpoint.

## 2026-03-13 (Longer Parameter Cache + Faster Failure Path)
- Bridge client now keeps separate cache windows:
  - `CURRENT_PARAMETERS` cache defaults to 30s
  - summary/status cache defaults to 3s
- Default live retry policy was shortened to fail fast on the local machine LAN:
  - `retry_count = 1`
  - `retry_delay_s = 0.2`
- Exposed a `status_snapshot()` helper for upper layers that merge async state into status resolution.
- Result: repeated `TTP` reads no longer re-download `CurrentParameters.xml` every second.

## 2026-03-13 (Batch Mapping Reads)
- Bridge client now exposes `read_mapped_values()` and forwards to the shared ZBC library.
- This is used by the main Raspi project to poll all mapped `TTE` / `TTW` states via one live summary read per cycle.

## 2026-03-13
- Bridge switched to `MAS-004_ZBC-Library`:
  - shared profile detection
  - shared ZBC transport/framing
  - shared summary parsing
  - shared current-parameter archive handling
- Added import shim `_zbc_library.py`:
  - uses installed package or sibling repo `../MAS-004_ZBC-Library`
- `service.py` extended:
  - real ZBC probe instead of raw TCP connect
  - `--summary-json`
  - `--read-current-parameter`
  - `--write-current-parameter`
  - `--read-mapping`
  - `--write-mapping`
- Corrected standard ZBC port in config to `3002`.
- Live confirmed:
  - `FTX[CURRENT_PARAMETERS]` accepted by the 6530
  - controlled writeback `JobUpdateReplyDelay 0 -> 1 -> 0`
- Bridge client can now resolve workbook-style `ZBC Mapping:` strings directly.

## 2026-03-04
- Added support memory files:
  - `docs/PROJECT_CONTEXT.md`
  - `docs/SUPPORT_RUNBOOK.md`
  - `docs/SUPPORT_CHANGELOG.md`
- Captured protocol-oriented support boundaries vs main Databridge.
- Baseline local HEAD during this entry: `556c73e`.

## Maintenance Rule
- Update this changelog on framing/checksum behavior, mapper/codec rules, deployment flow, or integration contract changes.
