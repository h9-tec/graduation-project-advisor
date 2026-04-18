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


async def _run_arxiv(days: int, max_records: int) -> None:
    from ingestion.pipelines.arxiv import fetch_recent

    candidates = await fetch_recent(days=days, max_records=max_records)
    result = await ingest(candidates)
    logger.info(f"done: {result}")


async def _run_github_trending(count: int) -> None:
    from ingestion.pipelines.github_trending import fetch_trending

    candidates = await fetch_trending(count=count)
    result = await ingest(candidates)
    logger.info(f"done: {result}")


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Run an ingestion pipeline one-shot.")
    parser.add_argument(
        "--source",
        required=True,
        choices=["hf_daily_papers", "arxiv", "github_trending"],
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="How many recent days to pull.",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=500,
        help="Cap for paginated sources (arxiv).",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=25,
        help="Number of trending repos to keep (github_trending).",
    )
    args = parser.parse_args()

    if args.source == "hf_daily_papers":
        await _run_hf_daily(args.days)
    elif args.source == "arxiv":
        await _run_arxiv(args.days, args.max_records)
    elif args.source == "github_trending":
        await _run_github_trending(args.count)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
