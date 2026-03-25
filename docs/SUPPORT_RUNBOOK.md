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
- Service active.
- Config values (`host`, `port`, `timeout_s`, `simulation`) are valid.
- Probe output stable (`zbc ok`/expected failures only).
- After a successful first probe, repeated probe cycles should not re-learn the transport profile unless config values changed or the service restarted.
- A single short timeout after recent success should appear as transient and should not immediately cause a warning/down-state flap.
- Manual live checks:
  - `python -m mas004_vj6530_zbc_bridge --config /etc/mas004_vj6530_zbc_bridge/config.json --summary-json`
  - `python -m mas004_vj6530_zbc_bridge --config /etc/mas004_vj6530_zbc_bridge/config.json --read-current-parameter System/TCPIP/BinaryCommsNetworkPort2`
  - `python -m mas004_vj6530_zbc_bridge --config /etc/mas004_vj6530_zbc_bridge/config.json --write-current-parameter System/TCPIP/JobUpdateReplyDelay 1`

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
