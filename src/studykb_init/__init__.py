"""StudyKB initialization tools module."""

__all__ = ["main"]


def main():
    """CLI entry point."""
    from studykb_init.cli import InitCLI
    import asyncio
    cli = InitCLI()
    asyncio.run(cli.run())


if __name__ == "__main__":
    main()
