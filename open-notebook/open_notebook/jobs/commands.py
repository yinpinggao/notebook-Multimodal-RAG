import asyncio
import inspect
from dataclasses import dataclass
from typing import Any, Callable, Optional
from uuid import uuid4

from loguru import logger
from pydantic import BaseModel

from .queue import job_queue
from .store import job_store


class ExecutionContext(BaseModel):
    command_id: str
    app_name: str
    command_name: str


class CommandInput(BaseModel):
    execution_context: Optional[ExecutionContext] = None


class CommandOutput(BaseModel):
    success: bool = True
    error_message: Optional[str] = None
    processing_time: Optional[float] = None

    def is_success(self) -> bool:
        return bool(self.success)


@dataclass
class RegisteredCommand:
    app_id: str
    name: str
    fn: Callable[..., Any]
    input_model: type[BaseModel]
    retry: Optional[dict[str, Any]]


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[tuple[str, str], RegisteredCommand] = {}

    def register(
        self,
        *,
        app_id: str,
        name: str,
        fn: Callable[..., Any],
        input_model: type[BaseModel],
        retry: Optional[dict[str, Any]],
    ) -> None:
        self._commands[(app_id, name)] = RegisteredCommand(
            app_id=app_id,
            name=name,
            fn=fn,
            input_model=input_model,
            retry=retry,
        )

    def get_command(self, app_id: str, name: str) -> RegisteredCommand:
        command = self._commands.get((app_id, name))
        if not command:
            raise ValueError(f"Unknown command: {app_id}.{name}")
        return command

    def get_all_commands(self) -> list[RegisteredCommand]:
        return sorted(
            self._commands.values(), key=lambda item: (item.app_id, item.name)
        )


registry = CommandRegistry()


def command(name: str, *, app: str, retry: Optional[dict[str, Any]] = None):
    def decorator(fn: Callable[..., Any]):
        signature = inspect.signature(fn)
        first_param = next(iter(signature.parameters.values()))
        input_model = first_param.annotation
        registry.register(
            app_id=app, name=name, fn=fn, input_model=input_model, retry=retry
        )
        return fn

    return decorator


def _retry_wait_seconds(retry: Optional[dict[str, Any]], attempt: int) -> float:
    if not retry:
        return 0.0
    wait_min = float(retry.get("wait_min", 1))
    wait_max = float(retry.get("wait_max", wait_min))
    return min(wait_max, wait_min * (2 ** max(0, attempt - 1)))


def _stop_retrying(exc: Exception, retry: Optional[dict[str, Any]]) -> bool:
    if not retry:
        return True
    stop_on = tuple(retry.get("stop_on") or [])
    return isinstance(exc, stop_on)


async def _run_registered_command(
    registered: RegisteredCommand,
    command_args: dict[str, Any],
    *,
    command_id: str,
) -> dict[str, Any]:
    attempts = max(1, int((registered.retry or {}).get("max_attempts", 1)))
    last_exc: Optional[Exception] = None
    for attempt in range(1, attempts + 1):
        try:
            input_payload = dict(command_args)
            input_payload["execution_context"] = ExecutionContext(
                command_id=command_id,
                app_name=registered.app_id,
                command_name=registered.name,
            ).model_dump()
            input_data = registered.input_model.model_validate(input_payload)
            result = await registered.fn(input_data)
            if isinstance(result, BaseModel):
                return result.model_dump(mode="json")
            return dict(result)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            last_exc = exc
            if attempt >= attempts or _stop_retrying(exc, registered.retry):
                raise
            await asyncio.sleep(_retry_wait_seconds(registered.retry, attempt))
    if last_exc:
        raise last_exc
    return {}


async def run_registered_command_job(*args: Any) -> dict[str, Any]:
    if len(args) == 1:
        job_id = args[0]
    elif len(args) == 2:
        _, job_id = args
    else:
        raise TypeError(
            "run_registered_command_job expects (job_id) or (ctx, job_id)"
        )

    record = await job_store.get_job_record(job_id)
    if not record:
        raise ValueError(f"Job {job_id} not found")
    if record.status == "cancelled":
        return {"cancelled": True}

    registered = registry.get_command(record.app_name, record.command_name)
    await job_store.update_job(job_id, status="running", started_at=job_store.now())

    try:
        result = await _run_registered_command(
            registered,
            record.args,
            command_id=job_id,
        )
        await job_store.update_job(
            job_id,
            status="completed",
            result=result,
            error_message=None,
            completed_at=job_store.now(),
        )
        return result
    except asyncio.CancelledError:
        await job_store.update_job(
            job_id,
            status="cancelled",
            completed_at=job_store.now(),
            error_message="Cancelled by user",
        )
        raise
    except Exception as exc:
        await job_store.update_job(
            job_id,
            status="failed",
            completed_at=job_store.now(),
            error_message=str(exc),
        )
        raise


async def async_submit_command(
    app_name: str,
    command_name: str,
    command_args: dict[str, Any],
    *,
    job_id: Optional[str] = None,
) -> str:
    registry.get_command(app_name, command_name)
    resolved_job_id = job_id or f"command:{uuid4().hex}"
    await job_store.create_job(
        app_name,
        command_name,
        command_args,
        job_id=resolved_job_id,
    )
    try:
        await job_queue.enqueue(resolved_job_id, run_registered_command_job)
    except Exception as exc:
        await job_store.update_job(
            resolved_job_id,
            status="failed",
            completed_at=job_store.now(),
            error_message=str(exc),
        )
        raise
    return resolved_job_id


def submit_command(app_name: str, command_name: str, command_args: dict[str, Any]) -> str:
    registry.get_command(app_name, command_name)
    job_id = f"command:{uuid4().hex}"

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            async_submit_command(
                app_name,
                command_name,
                command_args,
                job_id=job_id,
            )
        )

    task = loop.create_task(
        async_submit_command(
            app_name,
            command_name,
            command_args,
            job_id=job_id,
        )
    )

    def _log_schedule_failure(fut: asyncio.Future[str]) -> None:
        try:
            fut.result()
        except Exception as exc:
            logger.exception(exc)

    task.add_done_callback(_log_schedule_failure)
    return job_id


async def get_command_status(job_id: str):
    return await job_store.get_job(job_id)


async def cancel_command(job_id: str) -> bool:
    return await job_queue.cancel(job_id)


def execute_command_sync(
    app_name: str,
    command_name: str,
    command_args: dict[str, Any],
    timeout: Optional[int] = None,
):
    registered = registry.get_command(app_name, command_name)

    async def _run() -> CommandOutput:
        temp_command_id = f"command:sync:{app_name}:{command_name}"
        input_payload = dict(command_args)
        input_payload["execution_context"] = ExecutionContext(
            command_id=temp_command_id,
            app_name=app_name,
            command_name=command_name,
        ).model_dump()
        input_data = registered.input_model.model_validate(input_payload)
        coro = registered.fn(input_data)
        result = await asyncio.wait_for(coro, timeout=timeout) if timeout else await coro
        if isinstance(result, CommandOutput):
            return result
        return CommandOutput.model_validate(result)

    return asyncio.run(_run())
