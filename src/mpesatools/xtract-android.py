import re
import argparse
import json
import csv
import tempfile
from datetime import datetime, timedelta
from ledgerfy import ledgerfy_main
import subprocess
import sys


class MpesaParser:
    def __init__(self):
        self.patterns = [
            (
                re.compile(
                    r"(?P<receipt_number>[A-Z0-9]{8,10})\s+[Cc]onfirmed\.?\s*(?:(?P<buy_action>You bought)\s+)?Ksh(?P<amount>[\d,.]+)\s+(?P<details>(?P<action>sent to|paid to|of|transfered to)\s+(?P<name>.+?)(?: (?P<phone>\d{10})| for account (?P<account>.+?))?) on (?P<date>\d{1,2}/\d{1,2}/\d{2,4}) at (?P<time>\d{1,2}:\d{2} [AP]M)\.?[ \t]*(?:New\s+)?M-PESA balance is Ksh(?P<balance>[\d,.]+)\.(?:\s*Transaction cost, Ksh(?P<charge>[\d,.]+)\.?)?",
                    re.IGNORECASE,
                ),
                self._parse_sent,
            ),
            (
                re.compile(
                    r"(?P<receipt_number>[A-Z0-9]+)\s+Confirmed\.on\s+(?P<date>\d{1,2}/\d{1,2}/\d{2})\s+at\s+(?P<time>\d{1,2}:\d{2}\s+[APM]{2})Withdraw\s+Ksh(?P<amount>[\d,]+\.\d{2})\s+from\s+(?P<details>.*?)\s+New M-PESA balance is Ksh(?P<balance>[\d,]+\.\d{2})\.\s+Transaction cost,\s+Ksh(?P<charge>[\d,]+\.\d{2})",
                    re.IGNORECASE,
                ),
                self._parse_sent,
            ),
            (
                re.compile(
                    r"(?P<receipt_number>[A-Z0-9]{10})\s+[Cc]onfirmed\.?\s*(?:You have received\s+)?Ksh(?P<amount>[\d,.]+)\s+(?P<details>(?P<action>transferred from|from)\s+(?P<sender_source>.+?)(?:\s+in\s+(?P<location>[A-Z]{2,3}))?(?:\s+via\s+(?P<method>[\w\s]+?))?)\s+on\s+(?P<date>\d{1,2}/\d{1,2}/\d{2,4})\s+at\s+(?P<time>\d{1,2}:\d{2}\s+[AP]M)\.?(?:\s*M-Shwari balance is Ksh(?P<mshwari_balance>[\d,.]+)\s*\.?)?\s*(?:New\s+)?M-PESA balance is Ksh(?P<balance>[\d,.]+)\.?(?:\s*Transaction cost\s+Ksh\.?(?P<charge>[\d,.]+))?",
                    re.IGNORECASE,
                ),
                self._parse_received,
            ),
            (
                re.compile(
                    r"(?P<receipt_number>[A-Z0-9]+) Confirmed\. On (?P<date>\d{1,2}/\d{1,2}/\d{2}) at (?P<time>\d{1,2}:\d{2} [APM]+) Give Ksh(?P<amount>[\d,.]+) cash to (?P<details>.*?) New M-PESA balance is Ksh(?P<balance>[\d,.]+)\.",
                    re.IGNORECASE,
                ),
                self._parse_received,
            ),
        ]
        self.meta_patterns = {
            "balance": re.compile(r"balance is Ksh(?P<balance>[\d,.]+)", re.IGNORECASE),
            "charge": re.compile(
                r"Transaction cost, Ksh(?P<charge>[\d,.]+)", re.IGNORECASE
            ),
            "date": re.compile(r"on (?P<date>\d{1,2}/\d{1,2}/\d{2,4})", re.IGNORECASE),
            "time": re.compile(r"at (?P<time>\d{1,2}:\d{2} [AP]M)", re.IGNORECASE),
        }

    def _extract_metadata(self, sms):
        metadata = {}

        for key, pattern in self.meta_patterns.items():
            match = pattern.search(sms)
            if match:
                metadata[key] = match.group(1)
        return metadata

    def _clean_amount(self, amount_str):
        if not amount_str:
            return 0.0
        amount_str = amount_str.rstrip(".")
        amount_str = amount_str.replace(",", "")
        try:
            return float(amount_str)
        except ValueError:
            return 0.0

    def _clean_text(self, text):
        """Clean and normalize text data"""
        if not text:
            return ""

        # Remove extra whitespace and special characters
        text = str(text).strip()
        text = re.sub(r"\s+", " ", text)  # Replace multiple spaces with single space
        text = text.replace("\n", " ")  # Replace newlines with spaces

        return text

    def _parse_datetime(self, date_str, time_str):
        # match 8/1/26
        datetime_str = f"{date_str} {time_str}"
        datetime_object = datetime.strptime(datetime_str, "%d/%m/%y %I:%M %p")
        return datetime.strptime(
            datetime_object.strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S"
        )

    def _parse_sent(self, match, sms):
        # metadata
        # {'balance': '55,790.87.', 'charge': '0.00.', 'date': '8/1/26', 'time': '8:04 PM'}
        # {'balance': '56,512.87.', 'charge': '33.00.', 'date': '8/1/26', 'time': '11:52 AM'}

        metadata = self._extract_metadata(sms)
        amount = self._clean_amount(match.group("amount"))
        charge = self._clean_amount(match.group("charge"))
        balance = self._clean_amount(match.group("balance"))
        completion_time = self._parse_datetime(
            match.group("date") or metadata.get("date"),  #  '8/1/26'
            match.group("time") or metadata.get("time"),  #  '8:04 PM'
        )
        transactions = []
        # Receipt No,Completion Time,Details,Transaction Status,Paid In,Withdrawn,Balance
        transactions.append(
            {
                "Receipt No": match.group("receipt_number"),
                "Completion Time": completion_time,
                "Details": self._clean_text(match.group("details")),
                "Transaction Status": "Completed",
                "Paid In": "",
                "Withdrawn": f"{amount:.2f}",
                "Balance": f"{balance:.2f}",
            }
        )
        if charge > 0:
            transactions.append(
                {
                    "Receipt No": match.group("receipt_number"),
                    "Completion Time": completion_time,
                    "Details": "Mpesa Charge",
                    "Transaction Status": "Completed",
                    "Paid In": "",
                    "Withdrawn": f"{charge:.2f}",
                    "Balance": f"{balance:.2f}",
                }
            )
        return transactions

    def _parse_received(self, match, sms):
        metadata = self._extract_metadata(sms)

        amount = self._clean_amount(match.group("amount"))
        balance = self._clean_amount(match.group("balance"))

        completion_time = self._parse_datetime(
            match.group("date") or metadata.get("date"),  #  '8/1/26'
            match.group("time") or metadata.get("time"),  #  '8:04 PM'
        )
        transactions = []
        # Receipt No,Completion Time,Details,Transaction Status,Paid In,Withdrawn,Balance
        transactions.append(
            {
                "Receipt No": match.group("receipt_number"),
                "Completion Time": completion_time,
                "Details": self._clean_text(match.group("details")),
                "Transaction Status": "Completed",
                "Paid In": f"{amount:.2f}",
                "Withdrawn": "",
                "Balance": f"{balance:.2f}",
            }
        )
        return transactions

    def parse(self, sms):
        sms = sms.replace("\n", " ").strip()
        for pattern, callback in self.patterns:
            match = pattern.search(sms)
            if match:
                return callback(match, sms)


class MpesaMessages2CSV:
    def __init__(self):
        self.parser = MpesaParser()

    def fetch_sms(self):
        try:
            result = subprocess.run(
                [
                    "termux-sms-list",
                    '--message-selection=type == 1 and address == "MPESA"',
                    "-l",
                    "100",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            if result.returncode != 0:
                print("Error fetching SMS. Make sure termux-api is installed")
                return []

            try:
                sms_list = json.loads(result.stdout)
                if not isinstance(sms_list, list):
                    return []
                return sms_list
            except json.JSONDecodeError:
                return []
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            print(f"Error fetching SMS: {e}")
            return []

    def process_data(self):
        sms_list = self.fetch_sms()
        if not sms_list:
            print("No SMS found")
            return None
        all_transactions = []

        for sms in sms_list:
            transactions = self.parser.parse(sms.get("body", ""))
            if transactions:
                all_transactions.extend(transactions)
        if not all_transactions:
            print("No transactions found")
            return None

        return all_transactions

    def transactions_to_csv(self, transactions):
        tmp_csv = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        )
        fieldnames = [
            "Receipt No",
            "Completion Time",
            "Details",
            "Transaction Status",
            "Paid In",
            "Withdrawn",
            "Balance",
        ]

        writer = csv.DictWriter(tmp_csv, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(transactions)
        tmp_csv.close()
        return tmp_csv.name


if __name__ == "__main__":
    # For standalone execution
    import argparse

    parser = argparse.ArgumentParser(description="Convert M-Pesa SMS to Ledger format.")
    parser.add_argument(
        "--config",
        type=str,
        default="mpesa_rules.json",
        help="Path to the configuration file (JSON). Defaults to mpesa_rules.json",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Path to the output Ledger file.",
        default="output.bean",
    )
    parser.add_argument(
        "-s",
        "--start-date",
        type=str,
        default=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        help="Start date for processing transactions (YYYY-MM-DD).",
    )
    parser.add_argument(
        "-e",
        "--end-date",
        type=str,
        default=datetime.now().strftime("%Y-%m-%d"),
        help="End date for processing transactions (YYYY-MM-DD)",
    )

    # Process SMS
    mpesaB = MpesaMessages2CSV()
    transactions = mpesaB.process_data()

    if not transactions:
        print("No transactions found!")
        sys.exit(1)

    input_file = mpesaB.transactions_to_csv(transactions)
    print(f"Created CSV: {input_file}")

    # Create args for ledgerfy
    class Args:
        def __init__(self):
            args = parser.parse_args()
            self.input_file = input_file
            self.config = args.config
            self.output_file_path = args.output
            self.start_date = args.start_date
            self.end_date = args.end_date

    args = Args()

    # Call ledgerfy
    sys.exit(ledgerfy_main(args))
