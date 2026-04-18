"""One-shot ingestion CLI.

Usage:
    python -m ingestion.run --source hf_daily_papers --days 30
    python -m ingestion.run --source arxiv --days 2
    python -m ingestion.run --source github_trending
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from loguru import logger

from ingestion.upsert import ingest


async def _run_hf_daily(days: int) -> None:
    from ingestion.pipelines.hf_papers import fetch_recent

    candidates = await fetch_recent(days=days)
    result = await ingest(candidates)
    logger.info(f"done: {result}")


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Run an ingestion pipeline one-shot.")
    parser.add_argument(
        "--source",
        required=True,
        choices=["hf_daily_papers"],
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="How many recent days to pull (HF daily papers).",
    )
    args = parser.parse_args()

    if args.source == "hf_daily_papers":
        await _run_hf_daily(args.days)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
