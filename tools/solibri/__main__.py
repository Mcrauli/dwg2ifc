"""Entry point so ``python -m tools.solibri`` invokes the CLI."""

from tools.solibri.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
