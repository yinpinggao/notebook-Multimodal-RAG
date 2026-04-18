"""seekdb-commands integration for Open Notebook"""

from .artifact_commands import generate_artifact_command
from .compare_commands import compare_sources_command
from .eval_commands import run_project_eval_command
from .embedding_commands import (
    embed_insight_command,
    embed_note_command,
    embed_source_command,
    rebuild_embeddings_command,
)
from .example_commands import analyze_data_command, process_text_command
from .podcast_commands import generate_podcast_command
from .project_memory_commands import refresh_project_memory_command
from .project_commands import build_project_overview_command
from .seekdb_sync_commands import (
    backfill_seekdb_indexes,
    delete_seekdb_entity,
    resync_seekdb_note_scope,
    resync_seekdb_source_scope,
    sync_seekdb_credential,
    sync_seekdb_defaults,
    sync_seekdb_insight_index,
    sync_seekdb_model,
    sync_seekdb_note_index,
    sync_seekdb_source_chunks,
    sync_seekdb_source_pages,
)
from .source_commands import process_source_command
from .visual_rag_commands import index_visual_source_command

__all__ = [
    # Embedding commands
    "embed_note_command",
    "embed_insight_command",
    "embed_source_command",
    "rebuild_embeddings_command",
    # Other commands
    "generate_podcast_command",
    "generate_artifact_command",
    "process_source_command",
    "process_text_command",
    "analyze_data_command",
    "build_project_overview_command",
    "refresh_project_memory_command",
    "compare_sources_command",
    "run_project_eval_command",
    # SeekDB sync commands
    "sync_seekdb_credential",
    "sync_seekdb_model",
    "sync_seekdb_defaults",
    "sync_seekdb_source_pages",
    "sync_seekdb_source_chunks",
    "sync_seekdb_note_index",
    "sync_seekdb_insight_index",
    "resync_seekdb_source_scope",
    "resync_seekdb_note_scope",
    "delete_seekdb_entity",
    "backfill_seekdb_indexes",
    "index_visual_source_command",
]
