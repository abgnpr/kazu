"""Runtime configuration. Env vars are prefixed KAZU_ (e.g. KAZU_PORT=8765)."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_data_dir() -> Path:
    """XDG data dir, so the DB survives reinstalls and lives outside the repo."""
    return Path.home() / ".local" / "share" / "kazu"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KAZU_", env_file=".env", extra="ignore")

    # Bind to loopback only: this API has no business on the local network.
    host: str = "127.0.0.1"
    port: int = 8765

    data_dir: Path = _default_data_dir()
    db_name: str = "kazu.duckdb"

    # Shared secret the desktop shell sends as X-Kazu-Token. Empty disables the check,
    # which is the sane default while developing against the Vite dev server.
    auth_token: str = ""

    # Set false to run the API without the background refresh scheduler.
    enable_scheduler: bool = True

    @property
    def db_path(self) -> Path:
        return self.data_dir / self.db_name


settings = Settings()
