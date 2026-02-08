# MAS-004_VJ6530-ZBC-Bridge

Basis-Client fuer Videojet 6530 (TTO) ueber ZBC Binary Protocol.

## Enthalten
- `protocol.py`: Frame-Aufbau (A5/E4), Header-Checksum, CRC16, ACK/NAK.
- `client.py`: Synchronous TCP Client mit `transact`.
- `mapper.py`: Value-Codecs (`u16le`, `i32le`, `f32`, `ascii`) und Skalierung.

## Mapping von TTP auf ZBC
Fuer jede TTP-Variable wird mindestens benoetigt:
- `message_id` (z. B. `0x500A`)
- `command_id` (z. B. `0x0001`)
- optional `codec`, `scale`, `offset`

Ohne `command_id` ist keine eindeutige Zuordnung moeglich.

## Beispiel
```python
from mas004_vj6530_zbc_bridge import ZbcBridgeClient, ZbcMapping

cli = ZbcBridgeClient("192.168.2.30", 3007, timeout_s=2.0)
mapping = ZbcMapping(message_id=0x500A, command_id=0x0001, codec="u16le")
cli.write(mapping, "8")
print(cli.read(mapping))
```
