"""Command line for collecting and loading cases.

Usage (from backend/):
    python -m app.cli collect "State v. Example" --court "Delhi High Court"
    python -m app.cli load fixtures/jan-mat-v-state.json
    python -m app.cli load my-case.json --extract

`collect` runs the TinyFish agents (judgment, news, public comments), caches the
raw collection in fixtures/collected/, then extracts, anonymizes, scores and saves
it. `load` does the same for a case bundle you already have.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from app.agents import collect
from app.agents.base import AgentError, CaseQuery
from app.services.pipeline import PipelineError, run


async def collect_and_load(query: CaseQuery, refresh: bool) -> None:
    _, path = await collect(query, refresh)
    try:
        await run(path, force_extract=False)
    except PipelineError as err:
        raise PipelineError(
            f"{err} The collection is saved; load it later with: python -m app.cli load {path}"
        ) from err


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect and load Hetu cases.")
    commands = parser.add_subparsers(dest="command", required=True)

    c = commands.add_parser("collect", help="Collect a case with TinyFish agents, then load it")
    c.add_argument("name", help='Case name to search for, e.g. "State v. Example"')
    c.add_argument("--court", help="Court that decided the case, to narrow the search")
    c.add_argument("--category", default="Criminal Law")
    c.add_argument(
        "--refresh", action="store_true", help="Collect again even if this case was collected before"
    )

    load = commands.add_parser("load", help="Load case bundle files into the database")
    load.add_argument("files", nargs="+", type=Path)
    load.add_argument("--extract", action="store_true", help="Re-extract even if already extracted")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        if args.command == "collect":
            asyncio.run(collect_and_load(CaseQuery(args.name, args.court, args.category), args.refresh))
        else:
            for path in args.files:
                asyncio.run(run(path, args.extract))
    except (AgentError, PipelineError) as err:
        sys.exit(f"Error: {err}")


if __name__ == "__main__":
    main()
