from __future__ import annotations

import struct
from datetime import date, datetime
from dataclasses import dataclass
import threading
import time
from typing import Any

from .mapper import ZbcMapping, decode_value, encode_value
from ._zbc_library import (
    ClarityParameterArchive,
    CommandMapping,
    CurrentParameterMapping,
    ErrorStateMapping,
    MessageId,
    StatusMapping,
    ZbcClient,
    build_message,
    dataclass_to_dict,
    parse_message,
    parse_zbc_mapping,
    resolve_summary_mapping,
    resolve_summary_mappings,
    summary_to_status_values,
)


@dataclass(frozen=True)
class ProbeResult:
    profile_name: str
    machine_name: str
    machine_model: str
    job_name: str
    ribbon_level: str | None
    active_faults: tuple[str, ...]
    active_warnings: tuple[str, ...]


class ZbcBridgeClient:
    """Bridge-facing wrapper around the shared MAS-004 ZBC library."""

    def __init__(
        self,
        host: str,
        port: int,
        timeout_s: float = 8.0,
        retry_count: int = 1,
        retry_delay_s: float = 0.2,
        current_parameters_cache_ttl_s: float = 30.0,
        summary_cache_ttl_s: float = 3.0,
    ):
        self.host = (host or "").strip()
        self.port = int(port or 0)
        self.timeout_s = float(timeout_s)
        self.retry_count = max(1, int(retry_count))
        self.retry_delay_s = max(0.0, float(retry_delay_s))
        self.current_parameters_cache_ttl_s = max(0.0, float(current_parameters_cache_ttl_s or 0.0))
        self.summary_cache_ttl_s = max(0.0, float(summary_cache_ttl_s or 0.0))
        self._profile = None
        self._current_parameters_cache: ClarityParameterArchive | None = None
        self._current_parameters_cached_at = 0.0
        self._summary_cache: dict[str, Any] | None = None
        self._summary_cached_at = 0.0
        self._status_snapshot: dict[str, Any] = {}
        self._lock = threading.Lock()

    def write(self, mapping: ZbcMapping, value: str) -> tuple[int, bytes]:
        body = struct.pack("<H", mapping.command_id & 0xFFFF) + encode_value(value, mapping.codec, mapping.scale, mapping.offset)
        return self.transact(mapping.message_id, body)

    def read(self, mapping: ZbcMapping) -> str:
        body = struct.pack("<H", mapping.command_id & 0xFFFF)
        msg_id, payload = self.transact(mapping.message_id, body)
        if len(payload) >= 2 and struct.unpack("<H", payload[:2])[0] == (mapping.command_id & 0xFFFF):
            payload = payload[2:]
        return decode_value(payload, mapping.codec, mapping.scale, mapping.offset)

    def transact(self, message_id: int, body: bytes = b"") -> tuple[int, bytes]:
        if not self.host or self.port <= 0:
            raise RuntimeError("host/port not configured")
        return self._with_client(lambda client: parse_message(client._ensure_transport().exchange_message(build_message(message_id, body))), retries=1)

    def probe(self) -> ProbeResult:
        def _collect(client: ZbcClient):
            profile = client.profile or client.detect_profile()
            summary = client.request_summary_info()
            return profile, dataclass_to_dict(summary)

        profile, data = self._with_client(_collect)
        tags = {tag["name"]: tag["value"] for tag in data.get("tags", [])}
        machine = tags.get("mch") or {}
        job = tags.get("jin") or {}
        lei = tags.get("lei") or {}
        supplies = tags.get("sup") or {}
        ribbon_level = None
        for consumable in supplies.get("consumables", []):
            if consumable.get("type") == "Ribbon":
                ribbon_level = consumable.get("level")
                break
        return ProbeResult(
            profile_name=profile.name,
            machine_name=str(machine.get("name") or ""),
            machine_model=str(machine.get("model") or ""),
            job_name=str(job.get("name") or ""),
            ribbon_level=ribbon_level,
            active_faults=tuple(entry.get("name", "") for entry in lei.get("faults", [])),
            active_warnings=tuple(entry.get("name", "") for entry in lei.get("warnings", [])),
        )

    def request_current_parameters(self) -> ClarityParameterArchive:
        with self._lock:
            if self._current_parameters_cache is not None and self._cache_valid(self._current_parameters_cached_at, self.current_parameters_cache_ttl_s):
                return self._current_parameters_cache

        archive = self._with_client(lambda client: client.request_current_parameters(force_refresh=True))
        with self._lock:
            self._current_parameters_cache = archive
            self._current_parameters_cached_at = time.monotonic()
        return archive

    def read_current_parameter(self, path: str) -> str | None:
        leaf = self.request_current_parameters().find_by_path(path)
        return leaf.value if leaf is not None else None

    def read_mapped_value(self, mapping: str) -> str | None:
        spec = parse_zbc_mapping(mapping)
        if spec is None:
            raise ValueError(f"unsupported ZBC mapping: {mapping!r}")
        if isinstance(spec, CurrentParameterMapping):
            leaf = self.request_current_parameters().find_by_path(spec.path)
            return leaf.value if leaf is not None else None
        if isinstance(spec, (ErrorStateMapping, StatusMapping)):
            summary_payload = self.summary_dict(force_refresh=False)
            summary_dict = summary_payload.get("summary") or {}
            status_values = dict(summary_payload.get("status_values") or {})
            if isinstance(spec, ErrorStateMapping):
                return "1" if _has_matching_error_dict(summary_dict, spec) else "0"
            return _status_value_as_text(status_values, spec.name)
        if isinstance(spec, CommandMapping):
            return str(self._status_snapshot.get("last_command") or "")
        raise ValueError(f"unsupported ZBC mapping: {mapping!r}")

    def read_mapped_values(self, mappings: dict[str, str]) -> dict[str, str | None]:
        need_summary = False
        need_current = False
        parsed_specs: dict[str, Any] = {}
        for key, mapping in mappings.items():
            spec = parse_zbc_mapping(mapping)
            if spec is None:
                raise ValueError(f"unsupported ZBC mapping: {mapping!r}")
            parsed_specs[key] = spec
            need_current = need_current or isinstance(spec, CurrentParameterMapping)
            need_summary = need_summary or isinstance(spec, (ErrorStateMapping, StatusMapping))

        archive = self.request_current_parameters() if need_current else None
        summary_payload = self.summary_dict(force_refresh=False) if need_summary else None
        summary_dict = dict((summary_payload or {}).get("summary") or {})
        status_values = dict((summary_payload or {}).get("status_values") or {})
        resolved: dict[str, str | None] = {}
        for key, spec in parsed_specs.items():
            if isinstance(spec, CurrentParameterMapping):
                leaf = archive.find_by_path(spec.path) if archive is not None else None
                resolved[key] = leaf.value if leaf is not None else None
            elif isinstance(spec, ErrorStateMapping):
                resolved[key] = "1" if _has_matching_error_dict(summary_dict, spec) else "0"
            elif isinstance(spec, StatusMapping):
                resolved[key] = _status_value_as_text(status_values, spec.name)
            elif isinstance(spec, CommandMapping):
                resolved[key] = str(self._status_snapshot.get("last_command") or "")
            else:
                raise ValueError(f"unsupported ZBC mapping: {mappings[key]!r}")
        return resolved

    def write_current_parameters(self, archive: ClarityParameterArchive | bytes | bytearray | str, file_name: str = "CurrentParameters.xml") -> tuple[int, Any]:
        result = self._with_client(lambda client: client.write_current_parameters(archive, file_name=file_name))
        if result[0] == MessageId.NUL and isinstance(archive, ClarityParameterArchive):
            with self._lock:
                self._current_parameters_cache = archive
                self._current_parameters_cached_at = time.monotonic()
        else:
            self.invalidate_current_parameters_cache()
        self.invalidate_summary_cache()
        return result

    def write_current_parameter(self, path: str, value: str | int | float | bool, verify_readback: bool = True) -> tuple[int, str | None]:
        archive = self.request_current_parameters()
        archive.set_value(path, value)
        message_id, _response = self._with_client(lambda client: client.write_current_parameters(archive, file_name="CurrentParameters.xml"))
        verified = None
        if message_id == MessageId.NUL:
            with self._lock:
                self._current_parameters_cache = archive
                self._current_parameters_cached_at = time.monotonic()
            if verify_readback:
                verified_leaf = archive.find_by_path(path)
                verified = verified_leaf.value if verified_leaf is not None else None
        else:
            self.invalidate_current_parameters_cache()
        self.invalidate_summary_cache()
        return message_id, verified

    def write_mapped_value(self, mapping: str, value: str | int | float | bool, verify_readback: bool = True) -> tuple[int, str | None]:
        spec = parse_zbc_mapping(mapping)
        if spec is None:
            raise ValueError(f"unsupported ZBC mapping: {mapping!r}")
        if isinstance(spec, CurrentParameterMapping):
            return self.write_current_parameter(spec.path, value, verify_readback=verify_readback)
        if isinstance(spec, CommandMapping):
            message_id, _response = self._with_client(lambda client: client.write_mapped_value(mapping, value))
            if message_id == MessageId.NUL:
                with self._lock:
                    self._status_snapshot["last_command"] = str(value).strip().upper()
                    if self._status_snapshot["last_command"] in ("ONLINE", "START"):
                        self._status_snapshot["printer_online"] = True
                    elif self._status_snapshot["last_command"] in ("OFFLINE", "STOP", "SHUTDOWN"):
                        self._status_snapshot["printer_online"] = False
            self.invalidate_summary_cache()
            return message_id, str(value).strip().upper() if verify_readback else None
        raise ValueError(f"mapping is not writable: {mapping!r}")

    def summary_dict(self, force_refresh: bool = False) -> dict[str, Any]:
        with self._lock:
            if not force_refresh and self._summary_cache is not None and self._cache_valid(self._summary_cached_at, self.summary_cache_ttl_s):
                return dict(self._summary_cache)

        def _summary(client: ZbcClient):
            profile = client.profile or client.detect_profile()
            summary = client.request_summary_info()
            return profile, summary
        profile, summary = self._with_client(_summary)
        snapshot = dict(self._status_snapshot)
        summary_payload = {
            "profile": profile.name,
            "summary": _json_safe(dataclass_to_dict(summary)),
            "status_values": _json_safe(summary_to_status_values(summary, snapshot=snapshot)),
        }
        with self._lock:
            self._summary_cache = dict(summary_payload)
            self._summary_cached_at = time.monotonic()
        return summary_payload

    def _open_client(self) -> ZbcClient:
        return ZbcClient(
            self.host,
            self.port,
            timeout_s=self.timeout_s,
            profile=self._profile,
            cache_ttl_s=max(self.current_parameters_cache_ttl_s, self.summary_cache_ttl_s),
        )

    def _with_client(self, fn, retries: int | None = None):
        attempts = retries if retries is not None else self.retry_count
        last_error = None
        for attempt in range(1, attempts + 1):
            try:
                with self._open_client() as client:
                    result = fn(client)
                    self._profile = client.profile
                    return result
            except Exception as exc:
                last_error = exc
                if attempt >= attempts:
                    raise
                time.sleep(self.retry_delay_s)
        raise last_error  # pragma: no cover

    def update_status_snapshot(self, **values):
        with self._lock:
            self._status_snapshot.update(values)

    def status_snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._status_snapshot)

    def invalidate_current_parameters_cache(self):
        with self._lock:
            self._current_parameters_cache = None
            self._current_parameters_cached_at = 0.0

    def invalidate_summary_cache(self):
        with self._lock:
            self._summary_cache = None
            self._summary_cached_at = 0.0

    def _cache_valid(self, cached_at: float, ttl_s: float) -> bool:
        return ttl_s > 0.0 and (time.monotonic() - cached_at) <= ttl_s


def _json_safe(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def client_status_values(summary, snapshot: dict[str, Any]) -> dict[str, Any]:
    tags = {tag.name: tag.value for tag in summary.tags}
    sts = tags.get("sts")
    lei = tags.get("lei")
    state_flags = int(getattr(sts, "machine_state_flags", 0) or 0)
    fault = bool(state_flags & 0x00000004) or bool(getattr(lei, "faults", []) or [])
    warning = bool(state_flags & 0x00000008) or bool(getattr(lei, "warnings", []) or [])
    status = {
        "printer_online": bool(state_flags & int(0x00000002)),
        "printer_powered_down": bool(state_flags & 0x00000001),
        "printer_fault": fault,
        "printer_warning": warning,
        "printer_imaging": bool(state_flags & int(0x00000010)),
        "printer_active_error_type": int(getattr(sts, "active_error_type", 0) or 0),
        "printer_active_error_string": str(getattr(sts, "active_error_string", "") or ""),
    }
    if status["printer_powered_down"]:
        status["printer_state_text"] = "SHUTDOWN"
    elif status["printer_online"] and fault:
        status["printer_state_text"] = "ONLINE_FAULT"
    elif status["printer_online"] and warning:
        status["printer_state_text"] = "ONLINE_WARNING"
    elif status["printer_online"]:
        status["printer_state_text"] = "ONLINE"
    else:
        status["printer_state_text"] = "OFFLINE"
    status["printer_busy"] = bool(snapshot.get("printer_busy", False))
    status["printer_printing"] = bool(snapshot.get("printer_printing", False))
    status["last_command"] = snapshot.get("last_command")
    return status


def _status_value_as_text(status_values: dict[str, Any], name: str) -> str | None:
    value = status_values.get(
        {
            "PRINTER_ONLINE": "printer_online",
            "PRINTER_POWERED_DOWN": "printer_powered_down",
            "PRINTER_FAULT": "printer_fault",
            "PRINTER_WARNING": "printer_warning",
            "PRINTER_IMAGING": "printer_imaging",
            "PRINTER_BUSY": "printer_busy",
            "PRINTER_PRINTING": "printer_printing",
            "PRINTER_ACTIVE_ERROR_TYPE": "printer_active_error_type",
            "PRINTER_ACTIVE_ERROR_STRING": "printer_active_error_string",
            "PRINTER_STATE_TEXT": "printer_state_text",
        }.get((name or "").strip().upper(), ""),
    )
    if value is None:
        return None
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


def _has_matching_error_dict(summary_dict: dict[str, Any], mapping: ErrorStateMapping) -> bool:
    tags = {tag.get("name"): tag.get("value") for tag in summary_dict.get("tags", []) if isinstance(tag, dict)}
    lei = tags.get("lei") or {}
    entries = (lei.get("faults") if mapping.group == "fault" else lei.get("warnings")) or []
    for entry in entries:
        haystack = str(entry.get(mapping.field) or "").strip()
        if mapping.match_mode == "prefix" and haystack.startswith(mapping.needle):
            return True
        if mapping.match_mode == "exact" and haystack == mapping.needle:
            return True
    return False
