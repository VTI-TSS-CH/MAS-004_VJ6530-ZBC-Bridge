# MAS-004_VJ6530-ZBC-Bridge

Basis-Client und Daemon fuer Videojet 6530 (TTO) ueber ZBC Binary Protocol.

## Enthalten
- `protocol.py`: Frame-Aufbau (A5/E4), Header-Checksum, CRC16, ACK/NAK.
- `client.py`: Synchronous TCP Client mit `transact`.
- `mapper.py`: Value-Codecs und Skalierung.
- `service.py`: Daemon fuer Verbindung/Erreichbarkeitsprobe.

## Service-Dateien
- `systemd/mas004-vj6530-zbc-bridge.service`
- `scripts/install.sh`
- `scripts/run.sh`
- `scripts/default_config.json`

## Installation auf Raspi
```bash
cd /opt/MAS-004_VJ6530-ZBC-Bridge
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
chmod +x scripts/*.sh
./scripts/install.sh
```

## Config
`/etc/mas004_vj6530_zbc_bridge/config.json`

- `enabled`: Service aktiv/inaktiv
- `simulation`: wenn `true`, keine Live-Verbindung
- `host`, `port`: Drucker Endpoint
- `timeout_s`, `poll_interval_s`
