#!/usr/bin/env python
import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def load_config(config_path):
    """
    Load configuration from JSON file with validation
    """
    with open(config_path, "r") as config_file:
        config = json.load(config_file)

    # Validate configuration
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

    print(
        f"Configuration validated: {len(config['accounts'])} accounts, {len(config['rules'])} rules"
    )


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

        # Check if any exclude keywords match
        if any(exclude_keyword in details_lower for exclude_keyword in exclude):
            continue

        # Check if any keyword matches
        if any(keyword in details_lower for keyword in keywords):
            # If there's a condition, check it
            if condition:
                try:
                    if eval(condition, {"amount": amount}):
                        return rule["account"]
                except:
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


def main():
    parser = argparse.ArgumentParser(
        description="Convert M-Pesa CSV to Ledger format with balance."
    )
    parser.add_argument(
        "csv_file_path", type=str, help="Path to the input M-Pesa CSV file."
    )
    parser.add_argument(
        "--config",
        type=str,
        default="mpesa_categories.json",
        help="Path to the configuration file (JSON). Defaults to mpesa_categories.json",
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

    if not args.output_file_path:
        args.output_file_path = get_default_output_path(args.csv_file_path, "dat")

    try:
        parse_mpesa_to_ledger_with_balance(
            args.csv_file_path,
            args.output_file_path,
            args.start_date,
            args.end_date,
            args.config,
        )
    except ValueError as e:
        print(f"Configuration error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

# if __name__ == "__main__":
#     # sys.exit(main())
#     parse_mpesa_to_ledger_with_balance(
#         "/home/sato/.IT/python/projects/mpesa2csv/src/mpesa2csv/test/output_test.csv",
#         "/home/sato/.IT/python/projects/mpesa2csv/src/mpesa2csv/test/output_test.dat",
#         "2025-01-01",
#         None,
#         "/home/sato/.IT/python/projects/mpesa2csv/src/mpesa2csv/config.json",
#     )
