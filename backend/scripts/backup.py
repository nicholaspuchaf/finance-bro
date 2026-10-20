"""Create a consistent SQLite copy without stopping the API: uv run python scripts/backup.py."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings


def backup_database(source_path: Path, destination_dir: Path) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"finance_bro-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.db"
    with sqlite3.connect(source_path) as source, sqlite3.connect(destination) as target:
        source.backup(target)
    destination.chmod(0o600)
    return destination


if __name__ == "__main__":
    url = get_settings().database_url
    if not url.startswith("sqlite:///") or ":memory:" in url:
        raise SystemExit("O script de backup requer um arquivo SQLite local.")
    source = Path(url.removeprefix("sqlite:///" )).resolve()
    if not source.exists():
        raise SystemExit(f"Banco inexistente: {source}")
    print(backup_database(source, source.parent / "backups"))
