"""
User configuration for awsmap (~/.awsmap/config).
"""

import os


CONFIG_PATH = os.path.expanduser("~/.awsmap/config")

# Valid keys and their allowed values (None = any string)
_VALID_KEYS = {
    "profile":          None,
    "regions":          None,
    "services":         None,
    "format":           ("html", "json", "csv"),
    "workers":          "integer",
    "exclude_defaults": ("true", "false"),
    "db":               None,
    "query_format":     ("table", "json", "csv"),
    "required_tags":    None,
}


def get_config(key, default=None):
    """Read a config value by key. Returns default if not set."""
    if not os.path.exists(CONFIG_PATH):
        return default
    with open(CONFIG_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == key:
                    return v.strip()
    return default


def validate_config(key, value):
    """Validate a config key and value. Returns error message or None if valid."""
    if key not in _VALID_KEYS:
        valid = ", ".join(sorted(_VALID_KEYS))
        return f"Unknown key '{key}'. Valid keys: {valid}"
    allowed = _VALID_KEYS[key]
    if allowed is None:
        return None
    if allowed == "integer":
        if not value.isdigit() or int(value) < 1:
            return f"'{key}' must be a positive integer, got '{value}'"
        return None
    if isinstance(allowed, tuple):
        if value.lower() not in allowed:
            return f"'{key}' must be one of: {', '.join(allowed)}. Got '{value}'"
        return None
    return None


def set_config(key, value):
    """Set a config value. Raises ValueError for invalid key or value."""
    error = validate_config(key, value)
    if error:
        raise ValueError(error)
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    config = _read_all()
    config[key] = value
    _write_all(config)


def delete_config(key):
    """Delete a config key. No-op if key doesn't exist."""
    config = _read_all()
    if key in config:
        del config[key]
        _write_all(config)


def list_config():
    """Return all config as a dict (only valid keys)."""
    return _read_all()


def validate_file():
    """Validate the config file. Returns list of (line_num, error) for problems.

    Detects: bad format (missing =), unknown keys, invalid values.
    Auto-cleans by removing invalid entries and rewriting the file.
    """
    if not os.path.exists(CONFIG_PATH):
        return []
    errors = []
    clean = {}
    with open(CONFIG_PATH) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                errors.append((i, f"Bad format (missing '='): {line}"))
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            error = validate_config(k, v)
            if error:
                errors.append((i, error))
            else:
                clean[k] = v
    return errors


def _read_all():
    """Read all config into a dict. Skips invalid entries."""
    config = {}
    if not os.path.exists(CONFIG_PATH):
        return config
    with open(CONFIG_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if k in _VALID_KEYS and validate_config(k, v) is None:
                config[k] = v
    return config


def _write_all(config):
    """Write config dict to file."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        for k in sorted(config):
            f.write(f"{k}={config[k]}\n")
