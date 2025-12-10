#!/usr/bin/env python
"""
Ledger conversion module for mpesa-tools
"""

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from platformdirs import user_data_dir
import shutil


def load_config(config_path):
    """
    Load configuration from JSON file with validation
    """
    config_path = Path(config_path)

    if not config_path.exists():
        default_config = Path(__file__).parent / "mpesa_rules.json"
        if default_config.exists():
            config_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(default_config, config_path)
        else:
            raise ValueError(f"Config file '{config_path}' not found.")

    with config_path.open("r") as file:
        config = json.load(file)

    validate_config(config)

    return config


def validate_config(config):
    """
    Validate the configuration structure and content
    """
    # Check required fields
    required_fields = ["accounts", "rules", "default_account"]
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field in config: {field}")

    # Check that accounts is a list
    if not isinstance(config["accounts"], list):
        raise ValueError("'accounts' must be a list")

    # Check that rules is a list
    if not isinstance(config["rules"], list):
        raise ValueError("'rules' must be a list")

    # Check default_account is in accounts
    if config["default_account"] not in config["accounts"]:
        raise ValueError(
            f"default_account '{config['default_account']}' is not in accounts list"
        )

    # Check all rule accounts are in accounts
    for i, rule in enumerate(config["rules"]):
        if "account" not in rule:
            raise ValueError(f"Rule {i} is missing 'account' field")

        if rule["account"] not in config["accounts"]:
            raise ValueError(
                f"Rule {i} uses account '{rule['account']}' which is not in accounts list. "
                f"Please add it to the accounts list first."
            )

        # Validate rule structure
        if "keywords" not in rule:
            raise ValueError(f"Rule {i} is missing 'keywords' field")

        if not isinstance(rule["keywords"], list):
            raise ValueError(f"Rule {i} keywords must be a list")

        # Validate match_type if present
        if "match_type" in rule:
            match_type = rule["match_type"]
            if match_type not in ["any", "all"]:
                raise ValueError(
                    f"Rule {i} has invalid match_type '{match_type}'. Must be 'any' or 'all'."
                )

    print(
        f"Configuration validated: {len(config['accounts'])} accounts, {len(config['rules'])} rules"
    )


def check_keywords_match(details_lower, keywords, match_type="any", exclude=None):
    """
    Check if keywords match based on match_type (AND/OR logic)

    Args:
        details_lower: Transaction details in lowercase
        keywords: List of keywords to check
        match_type: "any" (OR logic, default) or "all" (AND logic)
        exclude: List of exclude keywords

    Returns:
        bool: True if keywords match according to match_type
    """
    if not keywords:
        return False

    # Check exclude keywords first
    if exclude and any(exclude_keyword in details_lower for exclude_keyword in exclude):
        return False

    # Check keywords based on match_type
    if match_type == "all":
        # AND logic: all keywords must be present
        return all(keyword in details_lower for keyword in keywords)
    else:
        # OR logic: any keyword must be present (default)
        return any(keyword in details_lower for keyword in keywords)


def categorize_transaction(details, amount, config):
    """
    Categorize transaction based on configuration
    """
    details_lower = details.lower()

    # Check each rule in order
    for rule in config["rules"]:
        keywords = rule.get("keywords", [])
        exclude = rule.get("exclude", [])
        condition = rule.get("condition")
        match_type = rule.get("match_type", "any")  # Default to "any" (OR logic)

        # Check if keywords match based on match_type
        if not check_keywords_match(details_lower, keywords, match_type, exclude):
            continue

        # If there's a condition, check it
        if condition:
            try:
                if eval(condition, {"amount": amount}):
                    return rule["account"]
            except Exception:
                # If condition evaluation fails, continue to next rule
                continue
        else:
            # No condition, return the account
            return rule["account"]

    # Return default account if no rule matches
    return config["default_account"]


def parse_mpesa_to_ledger_with_balance(
    input_file_path, output_file_path, start_date, end_date, config_path
):
    """
    Enhanced version with daily ending balance using config file
    """
    # Load configuration (with validation)
    config = load_config(config_path)

    transactions_by_date = defaultdict(list)
    with open(input_file_path, "r") as input_file:
        try:
            transactions = json.load(input_file)
        except json.JSONDecodeError:
            input_file.seek(0)
            content = input_file.read()
            content = content.lstrip("\ufeff")

            reader = csv.DictReader(content.splitlines())
            transactions = list(reader)

    for row in transactions:
        completion_time = row["Completion Time"]
        transaction_date = completion_time.split(" ")[0]

        if transaction_date < start_date:
            continue

        if end_date and transaction_date > end_date:
            continue

        details = row["Details"]
        status = row["Transaction Status"]
        paid_in = row["Paid In"]
        withdrawn = row["Withdrawn"]
        balance = row["Balance"]

        # Use ternary operator and convert to float only once
        paid_in = float(paid_in) if paid_in else 0.0
        withdrawn = float(withdrawn) if withdrawn else 0.0
        balance = float(balance) if balance else 0.0

        if status.lower() != "completed":
            continue

        # Determine amount and account
        if paid_in > 0:
            amount = paid_in
            account = categorize_transaction(details, amount, config)
        else:
            amount = withdrawn
            account = categorize_transaction(details, amount, config)

        transactions_by_date[transaction_date].append(
            {
                "account": account,
                "amount": amount,
                "details": details,
                "balance": balance,
                "timestamp": completion_time,
            }
        )
    # Check if we have any transactions in the date range
    if not transactions_by_date:
        print(
            f"No transactions found in the date range: {start_date} to {end_date or 'end of data'}"
        )
        return

    # Write ledger file with daily ending balance
    with open(output_file_path, "w", encoding="utf-8") as ledger_file:
        for date in sorted(transactions_by_date.keys()):
            ledger_file.write(f"{date} *\n")
            ledger_file.write("    Assets:Checking:Mpesa\n")

            # Sort transactions by timestamp to get the correct order
            daily_transactions = sorted(
                transactions_by_date[date], key=lambda x: x["timestamp"]
            )

            for i, transaction in enumerate(daily_transactions):
                account = transaction["account"]
                amount = transaction["amount"]
                details = transaction["details"]
                balance = transaction["balance"]

                # For expenses, amount is positive; for income, negative
                if account.startswith("Expenses"):
                    formatted_amount = f"{amount:15.2f} KES"
                else:
                    formatted_amount = f"{-amount:15.2f} KES"  # Negative for income

                # Truncate details if too long
                truncated_details = details

                # For the last transaction of the day, include balance
                if i == len(daily_transactions) - 1:
                    ledger_file.write(
                        f"    {account:<45} {formatted_amount} ; {truncated_details} BAL KES {balance:.2f}\n"
                    )
                else:
                    ledger_file.write(
                        f"    {account:<45} {formatted_amount} ; {truncated_details}\n"
                    )

            ledger_file.write("\n")

    # Print summary
    total_transactions = sum(
        len(transactions) for transactions in transactions_by_date.values()
    )
    print(f"Generated ledger file: {output_file_path}")
    date_range_str = (
        f"{start_date} to {end_date}"
        if end_date
        else f"{start_date} to {max(transactions_by_date.keys())}"
    )
    print(f"Processed {total_transactions} transactions from {date_range_str}")


def get_default_output_path(input_path, output_format):
    """Generate default output path based on input file and format"""
    input_path = Path(input_path)
    base_name = input_path.with_suffix("")
    return f"{base_name}.{output_format}"


def ledgerfy_main(args):
    """
    Main function for ledgerfy subcommand
    """
    if not Path(args.input_file).exists():
        print(f"Error: Input file '{args.input_file}' not found.")
        return 1

    if not args.output:
        args.output = get_default_output_path(args.input_file, "dat")

    try:
        parse_mpesa_to_ledger_with_balance(
            args.input_file,
            args.output,
            args.start_date,
            args.end_date,
            args.config,
        )
    except ValueError as e:
        print(f"Configuration error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    # For standalone execution
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert M-Pesa CSV to Ledger format with balance."
    )
    parser.add_argument(
        "csv_file_path", type=str, help="Path to the input M-Pesa CSV file."
    )
    parser.add_argument(
        "--config",
        type=str,
        default=Path(user_data_dir("mpesa-tools")) / "mpesa_rules.json",
        help="Path to the configuration file (JSON). Defaults to mpesa_rules.json",
    )
    parser.add_argument(
        "--output_file_path",
        type=str,
        help="Path to the output Ledger file. Defaults to mpesa_ledger_with_balance.dat",
    )
    parser.add_argument(
        "-s",
        "--start-date",
        type=str,
        default=str(datetime.now().year) + "-01-01",
        help="Start date for processing transactions (YYYY-MM-DD). Defaults to 2025-01-01",
    )
    parser.add_argument(
        "-e",
        "--end-date",
        type=str,
        help="End date for processing transactions (YYYY-MM-DD)",
    )

    args = parser.parse_args()
    sys.exit(ledgerfy_main(args))
