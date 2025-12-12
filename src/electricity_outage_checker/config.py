"""Configuration management for user settings."""

import json
from pathlib import Path

from .models import Address

CONFIG_DIR = Path.home() / ".config" / "shutdowns-checker"
CONFIG_FILE = CONFIG_DIR / "config.json"


class ConfigError(Exception):
    """Exception raised for configuration errors."""


def ensure_config_dir() -> None:
    """Ensure the configuration directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, str | dict[str, str]]:
    """Load configuration from file.

    Returns:
        Configuration dictionary.
    """
    if not CONFIG_FILE.exists():
        return {}

    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {}
            return data
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(config: dict[str, str | dict[str, str]]) -> None:
    """Save configuration to file.

    Args:
        config: Configuration dictionary to save.
    """
    ensure_config_dir()
    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_default_address() -> Address | None:
    """Get the default address from configuration.

    Returns:
        Default Address or None if not configured.
    """
    config = load_config()
    address_data = config.get("default_address")
    if not address_data or not isinstance(address_data, dict):
        return None

    city = address_data.get("city")
    street = address_data.get("street")
    house = address_data.get("house")

    if not all([city, street, house]):
        return None

    return Address(city=str(city), street=str(street), house=str(house))


def set_default_address(address: Address) -> None:
    """Set the default address in configuration.

    Args:
        address: Address to set as default.
    """
    config = load_config()
    config["default_address"] = {
        "city": address.city,
        "street": address.street,
        "house": address.house,
    }
    save_config(config)


def clear_default_address() -> None:
    """Clear the default address from configuration."""
    config = load_config()
    if "default_address" in config:
        del config["default_address"]
        save_config(config)
