# PROJECT_CONTEXT - MAS-004_VJ6530-ZBC-Bridge

## Role in MAS-004
- Subproject (not orchestration owner).
- Provides Videojet 6530 connectivity via ZBC binary protocol.
- Intended to be integrated by the main Databridge project.

## Repository Scope
- Package: `mas004_vj6530_zbc_bridge/`
- Shared library import shim: `_zbc_library.py`
- The shim also re-exports the preferred live 6530 transport profile constant so upper layers can open long-lived async sessions with the known-good profile first.
- The shim now also re-exports `snapshot_to_status_values()` so the Raspi async owner can normalize immediate AIR-driven state rows without reaching past the shared-library boundary.
- Bridge wrapper around `MAS-004_ZBC-Library`: `client.py`
- Each ad-hoc bridge client session now attempts `HCV` before executing the requested live operation.
- Legacy mapping/value codec support: `mapper.py`
- Probe service loop and CLI helpers: `service.py`
- Config model: `config.py`

## Protocol Summary
- Actual ZBC framing, profile detection and message parsing now come from `MAS-004_ZBC-Library`.
- This bridge keeps the 6530-specific operational layer:
  - summary probing
  - current-parameter read/write
  - batched workbook-mapping resolution for the Raspi poller
  - numeric printer-state mapping via `STATUS[PRINTER_STATE_CODE]`
  - legacy compatibility methods for raw mapped transactions

## Live Verified Capability
- `request_summary_info()` via shared library
- `request_current_parameters()` via `FRQ[CURRENT_PARAMETERS]`
- `write_current_parameters()` via `FTX[CURRENT_PARAMETERS]`
- `read_mapped_value("STATUS[PRINTER_STATE_CODE]")`
- `write_mapped_value("STATUS[PRINTER_STATE_CODE]", "<code>")` for the directly commandable target states `0`, `3`, `6`
- Live sequencing nuance on the TEST 6530:
  - `SHUTDOWN (6) -> OFFLINE (0)` via `STARTUP`
  - `OFFLINE (0) -> ONLINE (3)` via `START`
  - `SHUTDOWN (6) -> ONLINE (3)` therefore runs as `STARTUP` then `START`
- Derived state codes `1`, `2`, `4`, `5` are not direct control targets.
- Controlled live writeback proven on:
  - `System/TCPIP/JobUpdateReplyDelay`
  - value flow: `0 -> 1 -> 0`

## Runtime Paths
- Config: `/etc/mas004_vj6530_zbc_bridge/config.json`
- Systemd unit: `mas004-vj6530-zbc-bridge.service`
- Pi repo path: `/opt/MAS-004_VJ6530-ZBC-Bridge`

## Probe Runtime Notes
- The service probe loop keeps one `ZbcBridgeClient` per `(host, port, timeout_s)` tuple.
- Cached transport-profile knowledge survives between probe cycles and is only relearned after config changes or service restarts.
- The standalone service also uses a longer summary cache than the interactive client path.
- A single timeout after a recent successful probe is treated as transient to avoid warning/down-state flapping.
- The standalone daemon is a diagnostic/probe helper, not the operational owner of live 6530 traffic when the main Databridge already runs async/poll on the same Raspberry.
- On TEST, the standalone service is intentionally parked so the Databridge remains the sole owner of live `3002` sessions.
- For live Databridge ownership, prefer one long-lived owner session with keepalive over multiple parallel bridge/control sessions.

## Integration Boundary
- Repository focus is 6530-facing operations built on top of the shared library.
- Business parameter semantics stay in `MAS-004_RPI-Databridge`.
- ZBC async/status coverage is intentionally limited to status/event data; arbitrary printer-side `CURRENT_PARAMETERS` edits still require polling/readback in the main project.

## Last Reviewed
- Date: 2026-03-25
- Bridge now consumes `MAS-004_ZBC-Library` from sibling repo or installed package
