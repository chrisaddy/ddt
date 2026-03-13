from dataclasses import dataclass
import os
from pathlib import Path


def _first_env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


@dataclass(frozen=True)
class Settings:
    repo_root: Path = Path(__file__).resolve().parents[2]
    state_dir: Path = Path(__file__).resolve().parents[2] / "state"
    alpaca_api_key: str = _first_env("ALPACA_API_KEY", "ALPACA_KEY_ID")
    alpaca_api_secret: str = _first_env("ALPACA_API_SECRET", "ALPACA_SECRET_KEY")
    alpaca_base_url: str = _first_env("ALPACA_BASE_URL", default="https://paper-api.alpaca.markets")
    alpaca_data_url: str = _first_env("ALPACA_DATA_URL", default="https://data.alpaca.markets")


def get_settings() -> Settings:
    settings = Settings()
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    return settings


def validate_alpaca_settings(settings: Settings) -> Settings:
    missing = []
    if not settings.alpaca_api_key:
        missing.append('ALPACA_API_KEY/ALPACA_KEY_ID')
    if not settings.alpaca_api_secret:
        missing.append('ALPACA_API_SECRET/ALPACA_SECRET_KEY')
    if not settings.alpaca_base_url:
        missing.append('ALPACA_BASE_URL')
    if missing:
        raise ValueError('Missing Alpaca settings: ' + ', '.join(missing))
    return settings
