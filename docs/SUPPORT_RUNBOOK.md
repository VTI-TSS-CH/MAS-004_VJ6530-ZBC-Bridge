# SUPPORT_RUNBOOK - MAS-004_VJ6530-ZBC-Bridge

## 1. Positioning
- Subproject dependent on `MAS-004_RPI-Databridge` orchestration.
- Uses `MAS-004_ZBC-Library` as shared ZBC transport/message base.

## 2. Local Setup
- `python -m venv .venv`
- `.\.venv\Scripts\Activate.ps1`
- `python -m pip install -U pip`
- `python -m pip install -e .`

## 3. Pi Deployment
- Pull:
  - `ssh mas004-rpi "cd /opt/MAS-004_VJ6530-ZBC-Bridge && git pull --ff-only"`
- Restart:
  - `ssh mas004-rpi "sudo systemctl restart mas004-vj6530-zbc-bridge.service"`
- Logs:
  - `ssh mas004-rpi "sudo journalctl -u mas004-vj6530-zbc-bridge.service -n 120 --no-pager"`

## 4. Verification
- Service active only when this standalone daemon is intentionally used for diagnostics; when the main Databridge owns live 6530 traffic on the same Raspberry, keep this service disabled.
- Config values (`host`, `port`, `timeout_s`, `simulation`) are valid.
- Probe output stable (`zbc ok`/expected failures only).
- After a successful first probe, repeated probe cycles should not re-learn the transport profile unless config values changed or the service restarted.
- A single short timeout after recent success should appear as transient and should not immediately cause a warning/down-state flap.
- Manual live checks:
  - `python -m mas004_vj6530_zbc_bridge --config /etc/mas004_vj6530_zbc_bridge/config.json --summary-json`
  - `python -m mas004_vj6530_zbc_bridge --config /etc/mas004_vj6530_zbc_bridge/config.json --read-current-parameter System/TCPIP/BinaryCommsNetworkPort2`
  - `python -m mas004_vj6530_zbc_bridge --config /etc/mas004_vj6530_zbc_bridge/config.json --write-current-parameter System/TCPIP/JobUpdateReplyDelay 1`
  - `python - <<'PY'` / bridge client smoke check for `read_mapped_value("STATUS[PRINTER_STATE_CODE]")`
  - `python - <<'PY'` / bridge client smoke check for `write_mapped_value("STATUS[PRINTER_STATE_CODE]", "3")`
- For `STATUS[PRINTER_STATE_CODE]` verify the live transition path, not just the returned ACK:
  - `6 -> 0` through `STARTUP`
  - `0 -> 3` through `START`
  - `6 -> 3` through `STARTUP` then `START`
- Expect direct rejection for the derived targets `1`, `2`, `4`, `5`.
- Remember: generic printer-side `CURRENT_PARAMETERS` edits from the CLARiTY UI still do not surface as async ZBC events; the main Databridge must detect them via polling/readback.
- If the main Databridge async listener opens repeated long-lived sessions, verify that it consumes the exported `VJ6530_TCP_NO_CRC_PROFILE` from the bridge/library shim instead of forcing fresh profile probes on every session.
- If you need to open an interactive bridge/client session while the Databridge owns live async traffic, stop the Databridge first; the TEST 6530 timed out second parallel control sessions while the async owner session was already active.
- Do not leave this standalone probe daemon enabled in parallel with the Databridge on the same Raspberry unless a deliberate diagnostic session requires it.

## 5. Controlled Writeback Proof
- Live verified on 2026-03-13:
  - `System/TCPIP/JobUpdateReplyDelay`
  - `0 -> 1 -> 0`
  - each write acknowledged with `NUL`
  - each state verified by immediate reread

## 6. Sync Rule
- Use main repo scripts:
  - `MAS-004_RPI-Databridge/scripts/mas004_multirepo_status.ps1`
  - `MAS-004_RPI-Databridge/scripts/mas004_multirepo_sync.ps1`
- Never auto-overwrite dirty Pi repos.
