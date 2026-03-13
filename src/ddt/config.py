from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    repo_root: Path = Path(__file__).resolve().parents[2]
    state_dir: Path = Path(__file__).resolve().parents[2] / 'state'
    alpaca_api_key: str = os.getenv('ALPACA_API_KEY', '')
    alpaca_api_secret: str = os.getenv('ALPACA_API_SECRET', '')
    alpaca_base_url: str = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')


def get_settings() -> Settings:
    settings = Settings()
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    return settings
