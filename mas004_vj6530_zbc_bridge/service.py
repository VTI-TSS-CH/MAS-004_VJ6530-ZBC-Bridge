from __future__ import annotations

import argparse
import logging
import socket
import time

from mas004_vj6530_zbc_bridge.config import Settings, DEFAULT_CFG_PATH


def probe(cfg: Settings) -> tuple[bool, str]:
    if not cfg.host or int(cfg.port or 0) <= 0:
        return False, "host/port not configured"

    try:
        with socket.create_connection((cfg.host, int(cfg.port)), timeout=float(cfg.timeout_s)):
            return True, f"tcp ok: {cfg.host}:{cfg.port}"
    except Exception as exc:
        return False, f"tcp connect failed: {repr(exc)}"


def main() -> int:
    ap = argparse.ArgumentParser(description="MAS-004 VJ6530 ZBC bridge service")
    ap.add_argument("--config", default=DEFAULT_CFG_PATH)
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [VJ6530-ZBC] %(levelname)s %(message)s",
    )

    cfg_path = args.config
    last_state = None
    last_msg = ""
    last_cfg_reload = 0.0

    while True:
        now = time.time()
        if now - last_cfg_reload > 5.0:
            cfg = Settings.load(cfg_path)
            last_cfg_reload = now

        if not cfg.enabled:
            if last_state is not False or last_msg != "disabled":
                logging.info("service disabled in config")
            last_state = False
            last_msg = "disabled"
            time.sleep(max(0.2, float(cfg.poll_interval_s or 2.0)))
            continue

        if cfg.simulation:
            if last_state is not True or last_msg != "simulation":
                logging.info("simulation mode enabled")
            last_state = True
            last_msg = "simulation"
            time.sleep(max(0.2, float(cfg.poll_interval_s or 2.0)))
            continue

        ok, msg = probe(cfg)
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
