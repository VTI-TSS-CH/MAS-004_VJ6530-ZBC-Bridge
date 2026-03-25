from __future__ import annotations

import argparse
import json
import logging
import time

from mas004_vj6530_zbc_bridge.client import ZbcBridgeClient
from mas004_vj6530_zbc_bridge.config import Settings, DEFAULT_CFG_PATH


def _probe_client_key(cfg: Settings) -> tuple[str, int, float]:
    return ((cfg.host or "").strip(), int(cfg.port or 0), float(cfg.timeout_s or 0.0))


def probe(
    cfg: Settings,
    client: ZbcBridgeClient | None = None,
    client_factory=ZbcBridgeClient,
) -> tuple[bool, str, ZbcBridgeClient | None]:
    if not cfg.host or int(cfg.port or 0) <= 0:
        return False, "host/port not configured", None

    client = client or client_factory(cfg.host, int(cfg.port), timeout_s=float(cfg.timeout_s))
    try:
        snapshot = client.probe()
        msg = (
            f"zbc ok: {cfg.host}:{cfg.port} "
            f"profile={snapshot.profile_name} "
            f"machine={snapshot.machine_name or '-'} "
            f"job={snapshot.job_name or '-'} "
            f"faults={len(snapshot.active_faults)} "
            f"warnings={len(snapshot.active_warnings)} "
            f"ribbon={snapshot.ribbon_level or '-'}"
        )
        return True, msg, client
    except Exception as exc:
        return False, f"zbc probe failed: {repr(exc)}", client


def main() -> int:
    ap = argparse.ArgumentParser(description="MAS-004 VJ6530 ZBC bridge service")
    ap.add_argument("--config", default=DEFAULT_CFG_PATH)
    ap.add_argument("--summary-json", action="store_true", help="Print current ZBC summary as JSON and exit.")
    ap.add_argument("--read-current-parameter", default="", help="Read a current-parameter XML path and exit.")
    ap.add_argument("--write-current-parameter", nargs=2, metavar=("PATH", "VALUE"), help="Write a current-parameter XML path and verify it.")
    ap.add_argument("--read-mapping", default="", help="Read a workbook-style ZBC mapping and exit.")
    ap.add_argument("--write-mapping", nargs=2, metavar=("MAPPING", "VALUE"), help="Write a workbook-style ZBC mapping and verify it.")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [VJ6530-ZBC] %(levelname)s %(message)s",
    )

    cfg_path = args.config
    cfg = Settings.load(cfg_path)

    if args.summary_json or args.read_current_parameter or args.write_current_parameter or args.read_mapping or args.write_mapping:
        client = ZbcBridgeClient(cfg.host, int(cfg.port), timeout_s=float(cfg.timeout_s))
        if args.summary_json:
            print(json.dumps(client.summary_dict(), indent=2))
            return 0
        if args.read_current_parameter:
            print(client.read_current_parameter(args.read_current_parameter))
            return 0
        if args.write_current_parameter:
            path, value = args.write_current_parameter
            message_id, verified = client.write_current_parameter(path, value, verify_readback=True)
            print(json.dumps({"message_id": int(message_id), "verified_value": verified}, indent=2))
            return 0
        if args.read_mapping:
            print(client.read_mapped_value(args.read_mapping))
            return 0
        if args.write_mapping:
            mapping, value = args.write_mapping
            message_id, verified = client.write_mapped_value(mapping, value, verify_readback=True)
            print(json.dumps({"message_id": int(message_id), "verified_value": verified}, indent=2))
            return 0

    last_state = None
    last_msg = ""
    last_cfg_reload = 0.0
    probe_client = None
    probe_client_key = None

    while True:
        now = time.time()
        if now - last_cfg_reload > 5.0:
            cfg = Settings.load(cfg_path)
            last_cfg_reload = now

        current_probe_key = _probe_client_key(cfg)
        if current_probe_key != probe_client_key:
            probe_client = None
            probe_client_key = current_probe_key

        if not cfg.enabled:
            if last_state is not False or last_msg != "disabled":
                logging.info("service disabled in config")
            last_state = False
            last_msg = "disabled"
            probe_client = None
            time.sleep(max(0.2, float(cfg.poll_interval_s or 2.0)))
            continue

        if cfg.simulation:
            if last_state is not True or last_msg != "simulation":
                logging.info("simulation mode enabled")
            last_state = True
            last_msg = "simulation"
            probe_client = None
            time.sleep(max(0.2, float(cfg.poll_interval_s or 2.0)))
            continue

        ok, msg, probe_client = probe(cfg, client=probe_client)
        if ok != last_state or msg != last_msg:
            if ok:
                logging.info(msg)
            else:
                logging.warning(msg)
        last_state = ok
        last_msg = msg

        time.sleep(max(0.2, float(cfg.poll_interval_s or 2.0)))


if __name__ == "__main__":
    raise SystemExit(main())
