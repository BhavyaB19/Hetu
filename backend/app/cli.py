"""Load case bundles into the database.

Usage (from backend/):
    python -m app.cli fixtures/jan-mat-v-state.json
    python -m app.cli my-case.json --extract
"""

import argparse
import asyncio
import logging
from pathlib import Path

from app.services.pipeline import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Process case bundles into the database.")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--extract", action="store_true", help="Re-extract even if already extracted")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for path in args.files:
        asyncio.run(run(path, args.extract))


if __name__ == "__main__":
    main()
