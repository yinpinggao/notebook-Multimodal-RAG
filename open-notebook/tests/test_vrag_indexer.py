import json
from pathlib import Path

from open_notebook.vrag.indexer import VRAGIndexer


class FakeImageChunkStore:
    def __init__(self):
        self.rows: dict[str, dict] = {}

    def get_chunk(self, chunk_id: str):
        return self.rows.get(chunk_id)

    def list_chunks_by_source(self, source_id: str):
        return [row for row in self.rows.values() if row["source_id"] == source_id]

    def upsert_chunk(self, chunk_data: dict):
        self.rows[chunk_data["id"]] = dict(chunk_data)
        return chunk_data["id"]

    def update_chunk(self, chunk_id: str, update_data: dict):
        self.rows[chunk_id].update(update_data)
        return True

    def delete_source_chunks(self, source_id: str):
        to_delete = [chunk_id for chunk_id, row in self.rows.items() if row["source_id"] == source_id]
        for chunk_id in to_delete:
            del self.rows[chunk_id]
        return len(to_delete)


def test_index_source_rebuild_and_delete_use_image_chunk_store(monkeypatch, tmp_path):
    source_path = tmp_path / "sample.pdf"
    source_path.write_text("pdf-placeholder")
    image_path = tmp_path / "page-1.png"
    image_path.write_bytes(b"fake-image")

    monkeypatch.setattr(
        "open_notebook.vrag.indexer.extract_images_from_source",
        lambda **_: [{
            "page_no": 1,
            "image_index": 0,
            "image_path": str(image_path),
        }],
    )

    store = FakeImageChunkStore()
    indexer = VRAGIndexer(image_chunk_store=store)
    monkeypatch.setattr(indexer, "_encode_image_clip", lambda _: [0.1, 0.2, 0.3])
    monkeypatch.setattr(indexer, "_generate_image_summary", lambda *_args, **_kwargs: "A bar chart")

    index_result = indexer.index_source(
        source_id="source-1",
        source_path=str(source_path),
        generate_summaries=True,
    )

    assert index_result == {"total": 1, "indexed": 1, "skipped": 0, "errors": 0}
    stored_chunk = store.get_chunk("img_source-1_p1_i0")
    assert stored_chunk is not None
    assert json.loads(stored_chunk["embedding_json"]) == [0.1, 0.2, 0.3]
    assert stored_chunk["image_summary"] == "A bar chart"

    monkeypatch.setattr(indexer, "_encode_image_clip", lambda _: [0.4, 0.5, 0.6])
    monkeypatch.setattr(indexer, "_generate_image_summary", lambda *_args, **_kwargs: "Updated chart summary")

    rebuild_result = indexer.rebuild_index(
        source_id="source-1",
        regenerate_embeddings=True,
        regenerate_summaries=True,
    )

    assert rebuild_result == {"total": 1, "rebuilt": 1, "errors": 0}
    rebuilt_chunk = store.get_chunk("img_source-1_p1_i0")
    assert json.loads(rebuilt_chunk["embedding_json"]) == [0.4, 0.5, 0.6]
    assert rebuilt_chunk["image_summary"] == "Updated chart summary"

    deleted = indexer.delete_source_index("source-1")
    assert deleted == 1
    assert store.list_chunks_by_source("source-1") == []


def test_index_source_can_store_summary_without_vectors(monkeypatch, tmp_path):
    source_path = tmp_path / "sample.pdf"
    source_path.write_text("pdf-placeholder")
    image_path = tmp_path / "page-1.png"
    image_path.write_bytes(b"fake-image")

    monkeypatch.setattr(
        "open_notebook.vrag.indexer.extract_images_from_source",
        lambda **_: [{
            "page_no": 1,
            "image_index": 0,
            "image_path": str(image_path),
        }],
    )

    store = FakeImageChunkStore()
    indexer = VRAGIndexer(image_chunk_store=store)
    monkeypatch.setattr(indexer, "_encode_image_clip", lambda _: None)
    monkeypatch.setattr(indexer, "_generate_image_summary", lambda *_args, **_kwargs: "Screenshot of settings")

    result = indexer.index_source(
        source_id="source-2",
        source_path=str(source_path),
        generate_summaries=True,
    )

    assert result["indexed"] == 1
    stored_chunk = store.get_chunk("img_source-2_p1_i0")
    assert stored_chunk["embedding_json"] is None
    assert stored_chunk["image_summary"] == "Screenshot of settings"
