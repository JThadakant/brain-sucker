import argparse
import sys

__version__ = "0.1.0"


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="brainsuck")
    parser.add_argument("--version", action="version", version=f"brainsuck {__version__}")
    try:
        parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code or 0)
    parser.print_help()
    return 0
