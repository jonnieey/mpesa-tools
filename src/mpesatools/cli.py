#!/usr/bin/env python
"""
mpesa-tools: A unified CLI tool for M-Pesa transaction processing
"""

import argparse
import sys
from datetime import datetime

from .xtract import xtract_main
from .ledgerfy import ledgerfy_main
from . import __version__
from platformdirs import user_data_dir
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="M-Pesa Tools: Process M-Pesa transactions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mpesa-tools xtract statement.pdf -f csv
  mpesa-tools xtract statement.pdf -f json -o transactions.json
  mpesa-tools ledgerfy transactions.csv --config categories.json
  mpesa-tools ledgerfy transactions.csv -s 2024-01-01 -e 2024-12-31
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"mpesa-tools {__version__}",
        help="Show version information",
    )

    subparsers = parser.add_subparsers(
        title="subcommands",
        description="Available commands",
        dest="command",
        help="Choose a command to run",
    )

    # Add xtract subcommand
    xtract_parser = subparsers.add_parser(
        "xtract", help="Extract transactions from M-Pesa PDF statements"
    )
    xtract_parser.add_argument(
        "input_pdf", help="Path to the M-PESA PDF statement file"
    )
    xtract_parser.add_argument(
        "-f",
        "--format",
        choices=["csv", "json"],
        default="csv",
        help="Output format (default: csv)",
    )
    xtract_parser.add_argument(
        "-o",
        "--output",
        help="Output file path. If not provided, generated automatically from input file name",
    )
    xtract_parser.add_argument(
        "-s", "--summary", action="store_true", help="Show conversion summary"
    )

    # Add ledgerfy subcommand
    ledgerfy_parser = subparsers.add_parser(
        "ledgerfy", help="Convert M-Pesa CSV/JSON to Ledger format"
    )
    ledgerfy_parser.add_argument(
        "input_file", help="Path to the input M-Pesa CSV or JSON file"
    )
    ledgerfy_parser.add_argument(
        "--config",
        default=Path(user_data_dir("mpesa-tools")) / "mpesa_rules.json",
        help="Path to the configuration file (JSON). Defaults to mpesa_rules.json",
    )
    ledgerfy_parser.add_argument(
        "--output", help="Path to the output Ledger file. Defaults to <input_file>.dat"
    )
    ledgerfy_parser.add_argument(
        "-s",
        "--start-date",
        default=f"{datetime.now().year}-01-01",
        help="Start date for processing transactions (YYYY-MM-DD). Defaults to current year-01-01",
    )
    ledgerfy_parser.add_argument(
        "-e", "--end-date", help="End date for processing transactions (YYYY-MM-DD)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "xtract":
        return xtract_main(args)
    elif args.command == "ledgerfy":
        return ledgerfy_main(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
