from dataclasses import dataclass
import os
from pathlib import Path


def _first_env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {'1', 'true', 'yes', 'on'}


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == '':
        return default
    return float(value)


def _env_list(name: str) -> list[str]:
    value = os.getenv(name, '')
    return [item.strip().upper() for item in value.split(',') if item.strip()]


@dataclass(frozen=True)
class Settings:
    repo_root: Path = Path(__file__).resolve().parents[2]
    state_dir: Path = Path(__file__).resolve().parents[2] / 'state'
    alpaca_api_key: str = _first_env('ALPACA_API_KEY', 'ALPACA_KEY_ID')
    alpaca_api_secret: str = _first_env('ALPACA_API_SECRET', 'ALPACA_SECRET_KEY')
    alpaca_base_url: str = _first_env('ALPACA_BASE_URL', default='https://paper-api.alpaca.markets')
    alpaca_data_url: str = _first_env('ALPACA_DATA_URL', default='https://data.alpaca.markets')
    polygon_api_key: str = _first_env('POLYGON_API_KEY')
    polygon_base_url: str = _first_env('POLYGON_BASE_URL', default='https://api.polygon.io')
    ibkr_base_url: str = _first_env('IBKR_BASE_URL', default='https://localhost:5000/v1/api')
    ibkr_account_id: str = _first_env('IBKR_ACCOUNT_ID')
    ibkr_verify_ssl: bool = _env_bool('IBKR_VERIFY_SSL', False)
    max_order_notional: float = _env_float('DDT_MAX_ORDER_NOTIONAL', 250.0)
    banned_symbols: list[str] = None
    enforce_market_hours: bool = _env_bool('DDT_ENFORCE_MARKET_HOURS', True)

    def __post_init__(self):
        if self.banned_symbols is None:
            object.__setattr__(self, 'banned_symbols', _env_list('DDT_BANNED_SYMBOLS'))


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


def validate_polygon_settings(settings: Settings) -> Settings:
    missing = []
    if not settings.polygon_api_key:
        missing.append('POLYGON_API_KEY')
    if not settings.polygon_base_url:
        missing.append('POLYGON_BASE_URL')
    if missing:
        raise ValueError('Missing Polygon settings: ' + ', '.join(missing))
    return settings


def validate_ibkr_settings(settings: Settings) -> Settings:
    missing = []
    if not settings.ibkr_base_url:
        missing.append('IBKR_BASE_URL')
    if not settings.ibkr_account_id:
        missing.append('IBKR_ACCOUNT_ID')
    if missing:
        raise ValueError('Missing IBKR settings: ' + ', '.join(missing))
    return settings
