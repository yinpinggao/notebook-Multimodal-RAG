import pytest

from open_notebook.jobs import commands as job_commands


@pytest.mark.asyncio
async def test_async_submit_command_persists_and_enqueues(monkeypatch):
    seen: dict[str, object] = {}

    monkeypatch.setattr(
        job_commands.registry,
        "get_command",
        lambda app_name, command_name: (app_name, command_name),
    )

    async def fake_create_job(app_name, command_name, command_args, *, job_id=None):
        seen["create_job"] = (app_name, command_name, command_args, job_id)
        return job_id

    async def fake_enqueue(job_id, runner):
        seen["enqueue"] = (job_id, runner.__name__)

    monkeypatch.setattr(job_commands.job_store, "create_job", fake_create_job)
    monkeypatch.setattr(job_commands.job_queue, "enqueue", fake_enqueue)

    job_id = await job_commands.async_submit_command(
        "open_notebook",
        "index_visual_source",
        {"source_id": "source-1"},
        job_id="command:test",
    )

    assert job_id == "command:test"
    assert seen["create_job"] == (
        "open_notebook",
        "index_visual_source",
        {"source_id": "source-1"},
        "command:test",
    )
    assert seen["enqueue"] == ("command:test", "run_registered_command_job")
