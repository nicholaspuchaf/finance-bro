import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.categories import LEGACY_CATEGORIES
from app.config import ROOT_DIR
from app.database import Base, engine


def initialize_database() -> None:
    # A small, explicit migration for the first local schema. Replace with Alembic at deploy time.
    if engine.dialect.name != "sqlite":
        Base.metadata.create_all(bind=engine)
        return
    db_path = engine.url.database
    legacy = ROOT_DIR / "data" / "finance_bro.db"
    if db_path and db_path != ":memory:" and not Path(db_path).exists() and legacy.exists():
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(legacy) as source, sqlite3.connect(db_path) as target:
            source.backup(target)
    if db_path and db_path != ":memory:" and Path(db_path).exists():
        with sqlite3.connect(db_path) as source:
            columns = {row[1] for row in source.execute("PRAGMA table_info(transactions)")}
            if columns and {"classification_reason", "operation_type"} - columns:
                backup_path = Path(db_path).with_name(f"{Path(db_path).stem}.before-migration-{datetime.now(timezone.utc):%Y%m%d%H%M%S}.db")
                with sqlite3.connect(backup_path) as target:
                    source.backup(target)
                for name in ("classification_reason", "operation_type"):
                    if name not in columns:
                        source.execute(f"ALTER TABLE transactions ADD COLUMN {name} TEXT")
                source.commit()
    Base.metadata.create_all(bind=engine)
    if db_path and db_path != ":memory:":
        with sqlite3.connect(db_path) as source:
            placeholders = ",".join("?" for _ in LEGACY_CATEGORIES)
            has_legacy_categories = source.execute(
                f"SELECT 1 FROM transactions WHERE category IN ({placeholders}) LIMIT 1",
                tuple(LEGACY_CATEGORIES),
            ).fetchone()
            if has_legacy_categories:
                backup_path = Path(db_path).with_name(f"{Path(db_path).stem}.before-category-migration-{datetime.now(timezone.utc):%Y%m%d%H%M%S}.db")
                with sqlite3.connect(backup_path) as target:
                    source.backup(target)
                backup_path.chmod(0o600)
                source.executemany(
                    "UPDATE transactions SET category = ? WHERE category = ?",
                    [(new, old) for old, new in LEGACY_CATEGORIES.items()],
                )
                source.commit()
        Path(db_path).chmod(0o600)
    with engine.begin() as connection:
        duplicates = connection.exec_driver_sql("SELECT account_id, external_id FROM transactions WHERE account_id IS NOT NULL AND external_id IS NOT NULL GROUP BY account_id, external_id HAVING COUNT(*) > 1 LIMIT 1").first()
        if duplicates:
            raise RuntimeError("Transações Pluggy duplicadas no banco existente. Faça um backup e resolva as duplicatas antes de iniciar a API.")
        connection.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_account_external_transaction_idx ON transactions (account_id, external_id)")
