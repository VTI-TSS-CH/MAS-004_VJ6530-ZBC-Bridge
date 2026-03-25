from __future__ import annotations

from pathlib import Path
import sys


def _ensure_repo_on_path():
    candidates = []
    here = Path(__file__).resolve()
    candidates.extend(here.parents)
    cwd = Path.cwd().resolve()
    candidates.append(cwd)
    candidates.extend(cwd.parents)

    seen = set()
    for base in candidates:
        sibling_repo = base / "MAS-004_ZBC-Library"
        package_dir = sibling_repo / "mas004_zbc_library"
        sibling_repo_str = str(sibling_repo)
        if package_dir.exists() and sibling_repo_str not in seen:
            seen.add(sibling_repo_str)
            if sibling_repo_str not in sys.path:
                sys.path.insert(0, sibling_repo_str)


_ensure_repo_on_path()
from mas004_zbc_library import (  # type: ignore[attr-defined]
    AsyncSubscriptionId,
    ClarityParameterArchive,
    CommandMapping,
    CurrentParameterMapping,
    ErrorStateMapping,
    MessageId,
    StatusMapping,
    ZbcClient,
    dataclass_to_dict,
    parse_zbc_mapping,
    resolve_summary_mapping,
    resolve_summary_mappings,
    summary_to_status_values,
)
from mas004_zbc_library.framing import VJ6530_TCP_NO_CRC_PROFILE, build_message, parse_message


__all__ = [
    "ClarityParameterArchive",
    "AsyncSubscriptionId",
    "CommandMapping",
    "CurrentParameterMapping",
    "ErrorStateMapping",
    "MessageId",
    "StatusMapping",
    "VJ6530_TCP_NO_CRC_PROFILE",
    "ZbcClient",
    "build_message",
    "dataclass_to_dict",
    "parse_zbc_mapping",
    "parse_message",
    "resolve_summary_mapping",
    "resolve_summary_mappings",
    "summary_to_status_values",
]
