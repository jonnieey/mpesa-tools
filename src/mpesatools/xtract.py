#!/usr/bin/env python
"""
PDF extraction module for mpesa-tools
"""

import csv
import json
import os
import pdfplumber
import re
import sys
from pathlib import Path


def extract_mpesa_data_from_pdf(pdf_path):
    """
    Extract M-PESA transaction data from PDF statement
    """
    transactions = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Extract text from page
            text = page.extract_text()

            # Skip pages that don't contain transaction data
            if not text or "Receipt No." not in text:
                continue

            # Extract tables from the page
            tables = page.extract_tables()

            for table in tables:
                for row in table:
                    # Skip empty rows and header rows
                    if not row or len(row) < 6:
                        continue

                    # Skip rows that are clearly headers or separators
                    if any(
                        header in str(cell).lower()
                        for cell in row
                        if cell
                        for header in [
                            "receipt",
                            "completion",
                            "details",
                            "transaction",
                            "paid",
                            "withdrawn",
                            "balance",
                        ]
                    ):
                        continue

                    # Skip disclaimer and footer content
                    if any(
                        footer in str(cell)
                        for cell in row
                        if cell
                        for footer in [
                            "Disclaimer",
                            "Verification",
                            "For self-help",
                            "Page",
                        ]
                    ):
                        continue

                    # Process the transaction row
                    transaction = process_transaction_row(row)
                    if transaction:
                        transactions.append(transaction)

    return transactions


def process_transaction_row(row):
    """
    Process a single transaction row and extract relevant data
    Handles various edge cases in PDF formatting
    """
    try:
        # Skip rows that don't have enough data
        if len(row) < 7:
            return None

        receipt_no = clean_text(row[0])
        completion_time = clean_text(row[1])
        details = clean_text(row[2])
        transaction_status = clean_text(row[3])
        paid_in = clean_text(row[4])
        withdrawn = clean_text(row[5])
        balance = clean_text(row[6])

        # Skip if essential fields are missing
        if not receipt_no or not completion_time:
            return None

        # Handle transaction status - default to Completed if missing
        if not transaction_status:
            transaction_status = "Completed"

        # Clean and format amounts - convert to numbers or None
        paid_in_clean = clean_amount_to_number(paid_in)
        withdrawn_clean = clean_amount_to_number(withdrawn)
        balance_clean = clean_amount_to_number(balance)

        # Handle negative amounts in withdrawn column
        if withdrawn_clean is not None and withdrawn_clean < 0:
            withdrawn_clean = abs(withdrawn_clean)

        return {
            "receiptNo": receipt_no,
            "completionTime": completion_time,
            "details": details,
            "transactionStatus": transaction_status,
            "paidIn": paid_in_clean,
            "withdrawn": withdrawn_clean,
            "balance": balance_clean,
        }

    except Exception as e:
        print(f"Error processing row: {row}. Error: {e}")
        return None


def clean_text(text):
    """Clean and normalize text data"""
    if not text:
        return ""

    # Remove extra whitespace and special characters
    text = str(text).strip()
    text = re.sub(r"\s+", " ", text)  # Replace multiple spaces with single space
    text = text.replace("\n", " ")  # Replace newlines with spaces

    return text


def clean_amount_to_number(amount_str):
    """Clean amount strings and convert to float or return None"""
    if not amount_str:
        return None

    amount_str = str(amount_str).strip()

    # Remove currency symbols, commas, and extra characters
    amount_str = re.sub(r"[^\d.-]", "", amount_str)

    # Handle empty result after cleaning
    if not amount_str or amount_str == "-" or amount_str == ".":
        return None

    # Ensure proper decimal format
    if "." in amount_str:
        parts = amount_str.split(".")
        if len(parts) > 2:  # Handle multiple decimal points
            amount_str = parts[0] + "." + "".join(parts[1:])

    try:
        # Convert to float
        return float(amount_str)
    except ValueError:
        return None


def save_to_csv(transactions, output_path):
    """Save transactions to CSV file with the original header format"""
    if not transactions:
        print("No transactions to save")
        return False

    try:
        # Convert to CSV format with proper headers and string values
        csv_transactions = []
        for transaction in transactions:
            csv_transaction = {
                "Receipt No": transaction["receiptNo"],
                "Completion Time": transaction["completionTime"],
                "Details": transaction["details"],
                "Transaction Status": transaction["transactionStatus"],
                "Paid In": str(transaction["paidIn"])
                if transaction["paidIn"] is not None
                else "",
                "Withdrawn": str(transaction["withdrawn"])
                if transaction["withdrawn"] is not None
                else "",
                "Balance": str(transaction["balance"])
                if transaction["balance"] is not None
                else "",
            }
            csv_transactions.append(csv_transaction)

        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "Receipt No",
                "Completion Time",
                "Details",
                "Transaction Status",
                "Paid In",
                "Withdrawn",
                "Balance",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for transaction in csv_transactions:
                writer.writerow(transaction)

        print(
            f"Successfully converted {len(transactions)} transactions to {output_path}"
        )
        return True

    except Exception as e:
        print(f"Error saving to CSV: {e}")
        return False


def save_to_json(transactions, output_path):
    """Save transactions to JSON file in the specified format"""
    if not transactions:
        print("No transactions to save")
        return False

    json_transactions = []
    for transaction in transactions:
        json_transaction = {
            "Receipt No": transaction["receiptNo"],
            "Completion Time": transaction["completionTime"],
            "Details": transaction["details"],
            "Transaction Status": transaction["transactionStatus"],
            "Paid In": str(transaction["paidIn"])
            if transaction["paidIn"] is not None
            else "",
            "Withdrawn": str(transaction["withdrawn"])
            if transaction["withdrawn"] is not None
            else "",
            "Balance": str(transaction["balance"])
            if transaction["balance"] is not None
            else "",
        }
        json_transactions.append(json_transaction)
    try:
        with open(output_path, "w", encoding="utf-8") as jsonfile:
            json.dump(
                json_transactions,
                jsonfile,
                indent=2,
                ensure_ascii=False,
                default=json_serializer,
            )

        print(
            f"Successfully converted {len(transactions)} transactions to {output_path}"
        )
        return True

    except Exception as e:
        print(f"Error saving to JSON: {e}")
        return False


def json_serializer(obj):
    """Custom JSON serializer to handle special types"""
    if obj is None:
        return None
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def get_default_output_path(input_path, output_format):
    """Generate default output path based on input file and format"""
    input_path = Path(input_path)
    base_name = input_path.with_suffix("")
    return f"{base_name}.{output_format}"


def convert_mpesa_pdf(
    pdf_path, output_format="csv", output_path=None, show_summary=False
):
    """
    Main function to convert M-PESA PDF statement to CSV or JSON

    Args:
        pdf_path (str): Path to input PDF file
        output_format (str): Output format - 'csv' or 'json'
        output_path (str): Optional output file path

    Returns:
        bool: True if conversion successful, False otherwise
    """

    if output_format not in ["csv", "json"]:
        print(f"Error: Unsupported format '{output_format}'. Use 'csv' or 'json'.")
        return False

    if not output_path:
        output_path = get_default_output_path(pdf_path, output_format)

    print(f"Converting {pdf_path} to {output_path}...")

    # Extract data from PDF
    transactions = extract_mpesa_data_from_pdf(pdf_path)

    if not transactions:
        print("No transactions found in PDF")
        return False

    # Save to desired format
    if output_format == "csv":
        success = save_to_csv(transactions, output_path)
    else:  # json
        success = save_to_json(transactions, output_path)

    # Display summary
    if show_summary and success:
        total_transactions = len(transactions)
        total_deposits = sum(
            t["paidIn"] for t in transactions if t["paidIn"] is not None
        )
        total_withdrawals = sum(
            t["withdrawn"] for t in transactions if t["withdrawn"] is not None
        )

        print("\nConversion Summary:")
        print(f"Total Transactions: {total_transactions}")
        print(f"Total Deposits: {total_deposits:.2f}")
        print(f"Total Withdrawals: {total_withdrawals:.2f}")

    return success


def xtract_main(args):
    """
    Main function for xtract subcommand
    """
    if not os.path.isfile(args.input_pdf):
        print(f"Error: Input file '{args.input_pdf}' not found.")
        return 1

    success = convert_mpesa_pdf(
        pdf_path=args.input_pdf,
        output_format=args.format,
        output_path=args.output,
        show_summary=args.summary,
    )

    return 0 if success else 1


if __name__ == "__main__":
    # For standalone execution
    import argparse

    parser = argparse.ArgumentParser(description="Extract M-Pesa transactions from PDF")
    parser.add_argument("input_pdf", help="Path to the M-PESA PDF statement file")
    parser.add_argument(
        "-f", "--format", choices=["csv", "json"], default="csv", help="Output format"
    )
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("-s", "--summary", action="store_true", help="Show summary")

    args = parser.parse_args()
    sys.exit(xtract_main(args))
