# MAS-004_VJ6530-ZBC-Bridge

Bridge-Client und Daemon fuer Videojet 6530 (TTO) ueber ZBC Binary Protocol.

## Python fuer Schulung und Entwicklung
- Teamstandard fuer neue Entwicklungsrechner: `Python 3.13.x`
- `Python 3.12.x` ist als Fallback okay, wenn `3.13` auf dem Zielsystem nicht sauber verfuegbar ist
- `Python 3.14` derzeit nicht als Schulungsstandard verwenden
- `requires-python = ">=3.9"` im `pyproject.toml` beschreibt nur die technische Mindestversion, nicht die empfohlene Teamversion

## Enthalten
- `client.py`: Bridge-Wrapper auf `MAS-004_ZBC-Library`
- `_zbc_library.py`: Import/Fallback auf das benachbarte Repo `MAS-004_ZBC-Library`
- `mapper.py`: Legacy-Value-Codecs und Kompatibilitaets-Helfer
- `service.py`: Daemon und CLI fuer Probe, Summary, Current-Parameter-Read/Write

## Service-Dateien
- `systemd/mas004-vj6530-zbc-bridge.service`
- `scripts/install.sh`
- `scripts/run.sh`
- `scripts/default_config.json`

## Installation auf Raspi
```bash
cd /opt/MAS-004_VJ6530-ZBC-Bridge
python3.13 -m venv .venv
# alternativ auf Systemen ohne 3.13: python3.12 -m venv .venv
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

ZBC-Standardport fuer den 6530 ist hier `3002`.

Der Daemon behaelt seinen Probe-Client ueber die Poll-Zyklen hinweg und lernt das funktionierende Transportprofil nur neu an, wenn sich `host`, `port` oder `timeout_s` aendern.
Fuer den Standalone-Probe-Daemon wird die Summary zusaetzlich mit einem laengeren Cache-Fenster abgefedert; ein einzelner Timeout nach frischem Erfolg gilt nur als transient und erzeugt keinen sofortigen Down-Flap.

## Manuelle Live-Pruefung
```bash
cd /opt/MAS-004_VJ6530-ZBC-Bridge
./.venv/bin/python -m mas004_vj6530_zbc_bridge --config /etc/mas004_vj6530_zbc_bridge/config.json --summary-json
```

## Current-Parameter lesen
```bash
./.venv/bin/python -m mas004_vj6530_zbc_bridge --config /etc/mas004_vj6530_zbc_bridge/config.json \
  --read-current-parameter System/TCPIP/BinaryCommsNetworkPort2
```

## Current-Parameter schreiben
```bash
./.venv/bin/python -m mas004_vj6530_zbc_bridge --config /etc/mas004_vj6530_zbc_bridge/config.json \
  --write-current-parameter System/TCPIP/JobUpdateReplyDelay 1
```

## Workbook-Mapping lesen
```bash
./.venv/bin/python -m mas004_vj6530_zbc_bridge --config /etc/mas004_vj6530_zbc_bridge/config.json \
  --read-mapping "FRQ[CURRENT_PARAMETERS]/System/TCPIP/JobUpdateReplyDelay"
```

## Live verifiziert
- `MAS-004_ZBC-Library` ist jetzt die gemeinsame ZBC-Basis.
- `FTX` mit File-Typ `CURRENT_PARAMETERS (0x0009)` wurde gegen den echten 6530 erfolgreich verifiziert.
- Kontrollierter Writeback-Nachweis:
  - `System/TCPIP/JobUpdateReplyDelay` live `0 -> 1 -> 0`
  - jeder Schritt vom Drucker mit `NUL` bestaetigt und anschliessend wieder ausgelesen
