import asyncio
import os
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Literal, Optional, Tuple

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, field_validator

from open_notebook.domain.base import ObjectModel
from open_notebook.exceptions import DatabaseOperationError, InvalidInputError
from open_notebook.jobs import async_submit_command, get_command_status, submit_command
from open_notebook.seekdb import (
    ai_index_store,
    ai_retrieval_service,
    ai_sync_service,
    seekdb_business_store,
    use_seekdb_for_search,
)


class Notebook(ObjectModel):
    table_name: ClassVar[str] = "notebook"
    name: str
    description: str
    archived: Optional[bool] = False

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise InvalidInputError("Notebook name cannot be empty")
        return v

    async def get_sources(self) -> List["Source"]:
        try:
            srcs = await seekdb_business_store.list_notebook_sources(str(self.id))
            return [Source(**src) for src in srcs] if srcs else []
        except Exception as e:
            logger.error(f"Error fetching sources for notebook {self.id}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(e)

    async def get_notes(self) -> List["Note"]:
        try:
            srcs = await seekdb_business_store.list_notebook_notes(str(self.id))
            return [Note(**src) for src in srcs] if srcs else []
        except Exception as e:
            logger.error(f"Error fetching notes for notebook {self.id}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(e)

    async def get_chat_sessions(self) -> List["ChatSession"]:
        try:
            srcs = await seekdb_business_store.list_notebook_chat_sessions(str(self.id))
            return [ChatSession(**src) for src in srcs] if srcs else []
        except Exception as e:
            logger.error(
                f"Error fetching chat sessions for notebook {self.id}: {str(e)}"
            )
            logger.exception(e)
            raise DatabaseOperationError(e)

    async def get_delete_preview(self) -> Dict[str, Any]:
        """
        Get counts of items that would be affected by deleting this notebook.

        Returns a dict with:
        - note_count: Number of notes that will be deleted
        - exclusive_source_count: Sources only in this notebook (can be deleted)
        - shared_source_count: Sources in other notebooks (will be unlinked only)
        """
        try:
            return await seekdb_business_store.notebook_delete_preview(str(self.id))
        except Exception as e:
            logger.error(f"Error getting delete preview for notebook {self.id}: {e}")
            logger.exception(e)
            raise DatabaseOperationError(e)

    async def delete(self, delete_exclusive_sources: bool = False) -> Dict[str, int]:
        """
        Delete notebook with cascade deletion of notes and optional source deletion.

        Args:
            delete_exclusive_sources: If True, also delete sources that belong
                                     only to this notebook. Default is False.

        Returns:
            Dict with counts: deleted_notes, deleted_sources, unlinked_sources
        """
        if self.id is None:
            raise InvalidInputError("Cannot delete notebook without an ID")

        try:
            deleted_notes = 0
            deleted_sources = 0
            unlinked_sources = 0

            # 1. Get and delete all notes linked to this notebook
            notes = await self.get_notes()
            for note in notes:
                await note.delete()
                deleted_notes += 1
            logger.info(f"Deleted {deleted_notes} notes for notebook {self.id}")

            # Delete artifact relationships
            await seekdb_business_store.delete_relations(
                "artifact",
                target_id=str(self.id),
            )

            # 2. Handle sources
            if delete_exclusive_sources:
                # Find sources with count of references to OTHER notebooks
                # If assigned_others = 0, source is exclusive to this notebook
                source_ids = await seekdb_business_store.list_relation_sources(
                    "reference", str(self.id)
                )
                for source_id in source_ids:
                    total_refs = await seekdb_business_store.count_relations(
                        "reference", source_id=str(source_id)
                    )
                    if source_id and total_refs <= 1:
                        # Exclusive source - delete it
                        try:
                            source = await Source.get(str(source_id))
                            await source.delete()
                            deleted_sources += 1
                        except Exception as e:
                            logger.warning(
                                f"Failed to delete exclusive source {source_id}: {e}"
                            )
                    else:
                        unlinked_sources += 1
            else:
                # Just count sources that will be unlinked
                source_result = await seekdb_business_store.count_relations(
                    "reference", target_id=str(self.id)
                )
                unlinked_sources = source_result

            # Delete reference relationships (unlink all sources)
            await seekdb_business_store.delete_relations(
                "reference",
                target_id=str(self.id),
            )
            logger.info(
                f"Unlinked {unlinked_sources} sources, deleted {deleted_sources} "
                f"exclusive sources for notebook {self.id}"
            )

            # 3. Delete the notebook record itself
            await super().delete()
            logger.info(f"Deleted notebook {self.id}")

            return {
                "deleted_notes": deleted_notes,
                "deleted_sources": deleted_sources,
                "unlinked_sources": unlinked_sources,
            }

        except Exception as e:
            logger.error(f"Error deleting notebook {self.id}: {e}")
            logger.exception(e)
            raise DatabaseOperationError(f"Failed to delete notebook: {e}")


class Asset(BaseModel):
    file_path: Optional[str] = None
    url: Optional[str] = None


class SourceEmbedding(ObjectModel):
    table_name: ClassVar[str] = "source_embedding"
    source: Optional[str] = None
    order: Optional[int] = None
    content: str
    embedding: Optional[List[float]] = None

    async def get_source(self) -> "Source":
        try:
            embedding = await seekdb_business_store.get_entity(str(self.id))
            source_id = embedding.get("source") if embedding else None
            source = await seekdb_business_store.get_entity(str(source_id)) if source_id else None
            if not source:
                raise ValueError(f"Source not found for embedding {self.id}")
            return Source(**source)
        except Exception as e:
            logger.error(f"Error fetching source for embedding {self.id}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(e)


class SourceInsight(ObjectModel):
    table_name: ClassVar[str] = "source_insight"
    source: Optional[str] = None
    insight_type: str
    content: str

    async def get_source(self) -> "Source":
        try:
            source = await seekdb_business_store.get_entity(str(self.source))
            if not source:
                raise ValueError(f"Source not found for insight {self.id}")
            return Source(**source)
        except Exception as e:
            logger.error(f"Error fetching source for insight {self.id}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(e)

    async def save_as_note(self, notebook_id: Optional[str] = None) -> Any:
        source = await self.get_source()
        note = Note(
            title=f"{self.insight_type} from source {source.title}",
            content=self.content,
        )
        await note.save()
        if notebook_id:
            await note.add_to_notebook(notebook_id)
        return note

    async def delete(self) -> bool:
        deleted = await super().delete()
        if use_seekdb_for_search() and self.id:
            try:
                await ai_sync_service.delete_entity_index("insight", str(self.id))
            except Exception as e:
                logger.warning(
                    f"Failed to delete SeekDB insight index for {self.id}: {e}"
                )
        return deleted


class Source(ObjectModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    table_name: ClassVar[str] = "source"
    asset: Optional[Asset] = None
    title: Optional[str] = None
    topics: Optional[List[str]] = Field(default_factory=list)
    full_text: Optional[str] = None
    command: Optional[str] = Field(default=None, description="Link to processing job")

    @field_validator("command", mode="before")
    @classmethod
    def parse_command(cls, value):
        return str(value) if value else None

    @field_validator("id", mode="before")
    @classmethod
    def parse_id(cls, value):
        if value is None:
            return None
        return str(value) if value else None

    async def get_status(self) -> Optional[str]:
        """Get the processing status of the associated command"""
        if not self.command:
            return None

        try:
            status = await get_command_status(str(self.command))
            return status.status if status else "unknown"
        except Exception as e:
            logger.warning(f"Failed to get command status for {self.command}: {e}")
            return "unknown"

    async def get_processing_progress(self) -> Optional[Dict[str, Any]]:
        """Get detailed processing information for the associated command"""
        if not self.command:
            return None

        try:
            status_result = await get_command_status(str(self.command))
            if not status_result:
                return None

            # Extract execution metadata if available
            result = getattr(status_result, "result", None)
            execution_metadata = (
                result.get("execution_metadata", {}) if isinstance(result, dict) else {}
            )

            return {
                "status": status_result.status,
                "started_at": execution_metadata.get("started_at"),
                "completed_at": execution_metadata.get("completed_at"),
                "error": getattr(status_result, "error_message", None),
                "result": result,
            }
        except Exception as e:
            logger.warning(f"Failed to get command progress for {self.command}: {e}")
            return None

    async def get_context(
        self, context_size: Literal["short", "long"] = "short"
    ) -> Dict[str, Any]:
        insights_list = await self.get_insights()
        insights = [insight.model_dump() for insight in insights_list]
        if context_size == "long":
            return dict(
                id=self.id,
                title=self.title,
                insights=insights,
                full_text=self.full_text,
            )
        else:
            return dict(id=self.id, title=self.title, insights=insights)

    async def get_embedded_chunks(self) -> int:
        try:
            if use_seekdb_for_search():
                stats = await self.get_index_stats()
                return stats["chunk_count"]
            result = await seekdb_business_store.list_entities(
                "source_embedding", filters={"source": str(self.id)}
            )
            return len(result)
        except Exception as e:
            logger.error(f"Error fetching chunks count for source {self.id}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(f"Failed to count chunks for source: {str(e)}")

    async def get_page_count(self) -> int:
        try:
            if use_seekdb_for_search():
                stats = await self.get_index_stats()
                return stats["page_count"]
            return 0
        except Exception as e:
            logger.error(f"Error fetching page count for source {self.id}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(f"Failed to count pages for source: {str(e)}")

    async def get_index_stats(self) -> Dict[str, int]:
        try:
            if use_seekdb_for_search():
                return await ai_retrieval_service.source_page_stats(str(self.id))
            rows = await seekdb_business_store.list_entities(
                "source_embedding", filters={"source": str(self.id)}
            )
            chunk_count = len(rows)
            return {"page_count": 0, "chunk_count": chunk_count}
        except Exception as e:
            logger.error(f"Error fetching index stats for source {self.id}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(
                f"Failed to fetch index stats for source: {str(e)}"
            )

    async def get_insights(self) -> List[SourceInsight]:
        try:
            result = await seekdb_business_store.get_source_insights(str(self.id))
            return [SourceInsight(**insight) for insight in result]
        except Exception as e:
            logger.error(f"Error fetching insights for source {self.id}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError("Failed to fetch insights for source")

    async def add_to_notebook(self, notebook_id: str) -> Any:
        if not notebook_id:
            raise InvalidInputError("Notebook ID must be provided")
        result = await self.relate("reference", notebook_id)
        if use_seekdb_for_search() and self.id and self.full_text and self.full_text.strip():
            try:
                await async_submit_command(
                    "open_notebook",
                    "sync_seekdb_source_chunks",
                    {"source_id": str(self.id)},
                )
            except Exception as e:
                logger.warning(
                    f"Failed to queue SeekDB source resync for {self.id}: {e}"
                )
        return result

    async def vectorize(self) -> str:
        """
        Submit vectorization as a background job using the embed_source command.

        This method leverages the job-based architecture to prevent HTTP connection
        pool exhaustion when processing large documents. The embed_source command:
        1. Detects content type from file path
        2. Chunks text using content-type aware splitter
        3. Generates all embeddings in batches
        4. Bulk inserts source_embedding records

        Returns:
            str: The command/job ID that can be used to track progress via the commands API

        Raises:
            ValueError: If source has no text to vectorize
            DatabaseOperationError: If job submission fails
        """
        logger.info(f"Submitting embed_source job for source {self.id}")

        try:
            if not self.full_text or not self.full_text.strip():
                raise ValueError(f"Source {self.id} has no text to vectorize")

            # Submit the embed_source command
            command_id = await async_submit_command(
                "open_notebook",
                "embed_source",
                {"source_id": str(self.id)},
            )

            command_id_str = str(command_id)
            logger.info(
                f"Embed source job submitted for source {self.id}: "
                f"command_id={command_id_str}"
            )

            return command_id_str

        except ValueError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to submit embed_source job for source {self.id}: {e}"
            )
            logger.exception(e)
            raise DatabaseOperationError(e)

    async def add_insight(self, insight_type: str, content: str) -> Optional[str]:
        """
        Submit insight creation as an async command (fire-and-forget).

        Submits a create_insight command that handles database operations with
        automatic retry logic for transaction conflicts. The command also submits
        an embed_insight command for async embedding.

        This method returns immediately after submitting the command - it does NOT
        wait for the insight to be created. Use this for batch operations where
        throughput is more important than immediate confirmation.

        Args:
            insight_type: Type/category of the insight
            content: The insight content text

        Returns:
            command_id for optional tracking, or None if submission failed

        Raises:
            InvalidInputError: If insight_type or content is empty
        """
        if not insight_type or not content:
            raise InvalidInputError("Insight type and content must be provided")

        try:
            # Submit create_insight command (fire-and-forget)
            # Command handles retries internally for transaction conflicts
            command_id = await async_submit_command(
                "open_notebook",
                "create_insight",
                {
                    "source_id": str(self.id),
                    "insight_type": insight_type,
                    "content": content,
                },
            )
            logger.info(
                f"Submitted create_insight command {command_id} for source {self.id} "
                f"(type={insight_type})"
            )
            return str(command_id)

        except Exception as e:
            logger.error(f"Error submitting create_insight for source {self.id}: {e}")
            return None

    def _prepare_save_data(self) -> dict:
        data = super()._prepare_save_data()
        if data.get("command") is not None:
            data["command"] = str(data["command"])
        return data

    async def delete(self) -> bool:
        """Delete source and clean up associated file, embeddings, and insights."""
        insight_ids: list[str] = []
        if use_seekdb_for_search() and self.id:
            try:
                insight_ids = [insight.id or "" for insight in await self.get_insights()]
            except Exception:
                insight_ids = []

        # Clean up uploaded file if it exists
        if self.asset and self.asset.file_path:
            file_path = Path(self.asset.file_path)
            if file_path.exists():
                try:
                    os.unlink(file_path)
                    logger.info(f"Deleted file for source {self.id}: {file_path}")
                except Exception as e:
                    logger.warning(
                        f"Failed to delete file {file_path} for source {self.id}: {e}. "
                        "Continuing with database deletion."
                    )
            else:
                logger.debug(
                    f"File {file_path} not found for source {self.id}, skipping cleanup"
                )

        # Delete associated embeddings and insights to prevent orphaned records
        try:
            embeddings = await seekdb_business_store.list_entities(
                "source_embedding", filters={"source": str(self.id)}
            )
            for embedding in embeddings:
                await seekdb_business_store.delete_entity(str(embedding["id"]))
            insights = await seekdb_business_store.get_source_insights(str(self.id))
            for insight in insights:
                await seekdb_business_store.delete_entity(str(insight["id"]))
            logger.debug(f"Deleted embeddings and insights for source {self.id}")
        except Exception as e:
            logger.warning(
                f"Failed to delete embeddings/insights for source {self.id}: {e}. "
                "Continuing with source deletion."
            )

        if self.id:
            try:
                from open_notebook.storage.visual_assets import visual_asset_store

                await visual_asset_store.delete_source_assets(str(self.id))
                logger.debug(f"Deleted visual assets for source {self.id}")
            except Exception as e:
                logger.warning(
                    f"Failed to delete visual assets for source {self.id}: {e}. "
                    "Continuing with source deletion."
                )

        # Call parent delete to remove database record
        deleted = await super().delete()
        if use_seekdb_for_search() and self.id:
            try:
                await ai_sync_service.delete_entity_index("source", str(self.id))
                for insight_id in insight_ids:
                    if insight_id:
                        await ai_sync_service.delete_entity_index("insight", insight_id)
            except Exception as e:
                logger.warning(f"Failed to delete SeekDB source index for {self.id}: {e}")
        return deleted


class Note(ObjectModel):
    table_name: ClassVar[str] = "note"
    title: Optional[str] = None
    note_type: Optional[Literal["human", "ai"]] = None
    content: Optional[str] = None

    @field_validator("content")
    @classmethod
    def content_must_not_be_empty(cls, v):
        if v is not None and not v.strip():
            raise InvalidInputError("Note content cannot be empty")
        return v

    async def save(self) -> Optional[str]:
        """
        Save the note and submit embedding command.

        Overrides ObjectModel.save() to submit an async embed_note command
        after saving, instead of inline embedding.

        Returns:
            Optional[str]: The command_id if embedding was submitted, None otherwise
        """
        # Call parent save (without embedding)
        await super().save()

        # Submit embedding command (fire-and-forget) if note has content
        if self.id and self.content and self.content.strip():
            command_id = await async_submit_command(
                "open_notebook",
                "embed_note",
                {"note_id": str(self.id)},
            )
            logger.debug(f"Submitted embed_note command {command_id} for {self.id}")
            return command_id

        return None

    async def add_to_notebook(self, notebook_id: str) -> Any:
        if not notebook_id:
            raise InvalidInputError("Notebook ID must be provided")
        result = await self.relate("artifact", notebook_id)
        if use_seekdb_for_search() and self.id and self.content and self.content.strip():
            try:
                await async_submit_command(
                    "open_notebook",
                    "sync_seekdb_note_index",
                    {"note_id": str(self.id)},
                )
            except Exception as e:
                logger.warning(f"Failed to queue SeekDB note resync for {self.id}: {e}")
        return result

    async def delete(self) -> bool:
        deleted = await super().delete()
        if use_seekdb_for_search() and self.id:
            try:
                await ai_sync_service.delete_entity_index("note", str(self.id))
            except Exception as e:
                logger.warning(f"Failed to delete SeekDB note index for {self.id}: {e}")
        return deleted

    def get_context(
        self, context_size: Literal["short", "long"] = "short"
    ) -> Dict[str, Any]:
        if context_size == "long":
            return dict(id=self.id, title=self.title, content=self.content)
        else:
            return dict(
                id=self.id,
                title=self.title,
                content=self.content[:100] if self.content else None,
            )


class ChatSession(ObjectModel):
    table_name: ClassVar[str] = "chat_session"
    nullable_fields: ClassVar[set[str]] = {"model_override"}
    title: Optional[str] = None
    model_override: Optional[str] = None

    async def relate_to_notebook(self, notebook_id: str) -> Any:
        if not notebook_id:
            raise InvalidInputError("Notebook ID must be provided")
        return await self.relate("refers_to", notebook_id)

    async def relate_to_source(self, source_id: str) -> Any:
        if not source_id:
            raise InvalidInputError("Source ID must be provided")
        return await self.relate("refers_to", source_id)


async def text_search(
    keyword: str,
    results: int,
    source: bool = True,
    note: bool = True,
    source_ids: Optional[list[str]] = None,
    note_ids: Optional[list[str]] = None,
):
    if not keyword:
        raise InvalidInputError("Search keyword cannot be empty")
    try:
        return await ai_retrieval_service.text_search(
            keyword,
            results,
            source,
            note,
            source_ids=source_ids,
            note_ids=note_ids,
        )
    except Exception as e:
        logger.error(f"Error performing text search: {str(e)}")
        logger.exception(e)
        raise DatabaseOperationError(e)


async def vector_search(
    keyword: str,
    results: int,
    source: bool = True,
    note: bool = True,
    minimum_score=0.2,
    source_ids: Optional[list[str]] = None,
    note_ids: Optional[list[str]] = None,
):
    if not keyword:
        raise InvalidInputError("Search keyword cannot be empty")
    try:
        return await ai_retrieval_service.vector_search(
            keyword,
            results,
            source,
            note,
            minimum_score,
            source_ids=source_ids,
            note_ids=note_ids,
        )
    except Exception as e:
        logger.error(f"Error performing vector search: {str(e)}")
        logger.exception(e)
        raise DatabaseOperationError(e)
