import os
import re
from pathlib import Path


class VTTConfigurationError(RuntimeError):
    """Raised when a host has not supplied required VTT configuration."""


_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


def validate_identifier(value: str, label: str) -> str:
    """Validate an identifier before it is used in a path or authority check."""
    if not _IDENTIFIER_RE.fullmatch(value):
        raise ValueError(
            f"{label} must be 1-64 characters using letters, numbers, '.', '_', or '-'."
        )
    return value


def resolve_data_dir(storage_dir: str | Path | None = None) -> Path:
    """Resolve the host-owned VTT data directory.

    Library consumers must configure storage explicitly, either by passing a
    directory or setting VTT_DATA_DIR. This avoids writing into site-packages
    when VTT is installed as a wheel.
    """
    configured = storage_dir or os.environ.get("VTT_DATA_DIR")
    if not configured:
        raise VTTConfigurationError(
            "VTT storage is not configured. Pass storage_dir or set VTT_DATA_DIR."
        )
    return Path(configured).expanduser().resolve()
