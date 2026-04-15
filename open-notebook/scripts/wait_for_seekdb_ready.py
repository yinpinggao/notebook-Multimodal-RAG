#!/usr/bin/env python3
import argparse
import asyncio
import time

from open_notebook.seekdb import seekdb_client


async def main(timeout: int) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            await seekdb_client.ensure_schema()
            if await seekdb_client.ping():
                print("SeekDB is ready")
                return
        except Exception as exc:
            last_error = exc
        await asyncio.sleep(3)

    raise SystemExit(f"SeekDB was not ready within {timeout}s: {last_error}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wait until SeekDB is ready.")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    asyncio.run(main(args.timeout))
