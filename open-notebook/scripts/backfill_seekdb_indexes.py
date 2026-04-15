#!/usr/bin/env python3
import argparse
import asyncio
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from commands.embedding_commands import (
    EmbedInsightInput,
    EmbedNoteInput,
    EmbedSourceInput,
    collect_items_for_rebuild,
    embed_insight_command,
    embed_note_command,
    embed_source_command,
)
from open_notebook.database.async_migrate import AsyncMigrationManager


async def backfill_indexes(args: argparse.Namespace) -> None:
    await AsyncMigrationManager().run_migration_up()

    started_at = time.time()
    items = await collect_items_for_rebuild(
        args.mode,
        include_sources=args.include_sources,
        include_notes=args.include_notes,
        include_insights=args.include_insights,
    )

    summary = {"sources": 0, "notes": 0, "insights": 0, "failed": 0}

    for source_id in items["sources"]:
        result = await embed_source_command(EmbedSourceInput(source_id=source_id))
        summary["sources"] += 1 if result.success else 0
        summary["failed"] += 0 if result.success else 1

    for note_id in items["notes"]:
        result = await embed_note_command(EmbedNoteInput(note_id=note_id))
        summary["notes"] += 1 if result.success else 0
        summary["failed"] += 0 if result.success else 1

    for insight_id in items["insights"]:
        result = await embed_insight_command(EmbedInsightInput(insight_id=insight_id))
        summary["insights"] += 1 if result.success else 0
        summary["failed"] += 0 if result.success else 1

    elapsed = time.time() - started_at
    print("SeekDB index backfill complete.")
    print(f"sources: {summary['sources']}")
    print(f"notes: {summary['notes']}")
    print(f"insights: {summary['insights']}")
    print(f"failed: {summary['failed']}")
    print(f"elapsed_seconds: {elapsed:.2f}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill SeekDB search indexes.")
    parser.add_argument("--mode", choices=["existing", "all"], default="all")
    parser.add_argument("--skip-sources", action="store_true")
    parser.add_argument("--skip-notes", action="store_true")
    parser.add_argument("--skip-insights", action="store_true")
    args = parser.parse_args()
    args.include_sources = not args.skip_sources
    args.include_notes = not args.skip_notes
    args.include_insights = not args.skip_insights
    return args


if __name__ == "__main__":
    asyncio.run(backfill_indexes(parse_args()))
