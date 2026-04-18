from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.evidence.structured_extractor import SourceProfile
from open_notebook.project_os.overview_service import build_and_store_project_overview


@pytest.mark.asyncio
@patch(
    "open_notebook.project_os.overview_service.save_project_overview_snapshot",
    new_callable=AsyncMock,
)
@patch(
    "open_notebook.project_os.overview_service.build_and_store_source_profile",
    new_callable=AsyncMock,
)
@patch(
    "open_notebook.project_os.overview_service.Notebook.get",
    new_callable=AsyncMock,
)
async def test_build_and_store_project_overview_skips_failed_source_profiles(
    mock_get_notebook,
    mock_build_profile,
    mock_save_snapshot,
):
    notebook = SimpleNamespace(
        created="2026-04-18T08:00:00Z",
        get_sources=AsyncMock(
            return_value=[
                SimpleNamespace(id="source:good"),
                SimpleNamespace(id="source:bad"),
            ]
        ),
    )
    mock_get_notebook.return_value = notebook
    mock_build_profile.side_effect = [
        SourceProfile(
            source_id="source:good",
            title="Good Source",
            generated_at="2026-04-18T08:10:00Z",
            topics=["项目画像"],
            keywords=["项目画像", "证据优先"],
            risks=["证据覆盖不足"],
        ),
        RuntimeError("broken source"),
    ]
    mock_save_snapshot.side_effect = lambda snapshot: snapshot

    snapshot = await build_and_store_project_overview("project:demo")

    assert snapshot.project_id == "project:demo"
    assert snapshot.topics == ["项目画像"]
    assert snapshot.risks == ["证据覆盖不足"]
    assert len(snapshot.source_profiles) == 1
