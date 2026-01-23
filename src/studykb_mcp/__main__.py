"""Main entry point for studykb-mcp."""

import asyncio

from .server import run_server


def main() -> None:
    """Main entry point."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
