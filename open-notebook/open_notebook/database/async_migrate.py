from datetime import datetime

from loguru import logger

from open_notebook.seekdb import seekdb_business_store, seekdb_client


class AsyncMigrationManager:
    TARGET_VERSION = 1

    async def get_current_version(self) -> int:
        try:
            await seekdb_client.ensure_schema()
            row = await seekdb_client.fetch_one(
                "SELECT version FROM schema_migrations WHERE id = %s",
                ("open_notebook",),
            )
            return int((row or {}).get("version") or 0)
        except Exception:
            return 0

    async def needs_migration(self) -> bool:
        return await self.get_current_version() < self.TARGET_VERSION

    async def run_migration_up(self):
        await seekdb_client.ensure_schema()
        await seekdb_business_store.ensure_schema()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await seekdb_client.execute(
            """
            INSERT INTO schema_migrations (id, version, created, updated)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                version = VALUES(version),
                updated = VALUES(updated)
            """,
            ("open_notebook", self.TARGET_VERSION, now, now),
        )
        logger.info("SeekDB schema migration applied")
