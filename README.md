# M-Pesa Tools

A command-line toolkit for processing M-Pesa transactions. Extract data from PDF statements and convert to accounting formats with smart categorization.

## Features

-   **PDF Extraction:** Convert M-Pesa PDF statements to CSV or JSON.
-   **Ledger Conversion:** Convert transaction data to Ledger-cli format.
-   **Smart Categorization:** Configurable rules with AND/OR logic and conditions.
-   **Date Filtering:** Process specific date ranges.
-   **Balance Tracking:** Include daily ending balances in ledger output.

## Installation

### From PyPI

```bash
pip install mpesa-tools
```

### From Source

```bash
git clone https://github.com/jonnieey/mpesa-tools.git
cd mpesa-tools
pip install -e .
```

## Quick Start

```bash
# Extract transactions from PDF
mpesa-tools xtract statement.pdf -f csv

# Convert to ledger format
mpesa-tools ledgerfy transactions.csv

# View help
mpesa-tools --help
```

## Commands

### `xtract`: Extract from PDF

Extract transaction data from M-Pesa PDF statements.

```bash
mpesa-tools xtract INPUT_PDF [OPTIONS]
```

**Options:**

-   `-f, --format`: Output format (csv or json, default: csv)
-   `-o, --output`: Output file path
-   `-s, --summary`: Show conversion summary

**Examples:**

```bash
mpesa-tools xtract statement.pdf
mpesa-tools xtract statement.pdf -f json -o data.json --summary
```

### `ledgerfy`: Convert to Ledger Format

Convert CSV/JSON transaction data to Ledger-cli format with categorization.

```bash
mpesa-tools ledgerfy INPUT_FILE [OPTIONS]
```

**Options:**

-   `--config`: Path to configuration file (default: `mpesa_categories.json`)
-   `--output`: Output file path (default: `input_file.dat`)
-   `-s, --start-date`: Start date (YYYY-MM-DD, default: current year-01-01)
-   `-e, --end-date`: End date (YYYY-MM-DD)

**Examples:**

```bash
mpesa-tools ledgerfy transactions.csv
mpesa-tools ledgerfy data.json --config my_rules.json -s 2024-01-01
mpesa-tools ledgerfy transactions.csv --start-date 2024-01-01 --end-date 2024-12-31 --output mpesa_2024.dat
```

## Configuration

Create a `mpesa_categories.json` file to define categorization rules:

```json
{
  "accounts": ["Expenses:Food", "Expenses:Transport"],
  "rules": [
    {
      "keywords": ["restaurant", "hotel"],
      "account": "Expenses:Food"
    },
    {
      "keywords": ["uber", "taxi"],
      "account": "Expenses:Transport"
    }
  ],
  "default_account": "Expenses:Misc"
}
```

For advanced configuration including AND/OR logic, conditions, and exclude keywords, see [USAGE.md](USAGE.md).

## Project Structure

```text
mpesa2csv/
├── src/mpesa2csv/
│   ├── __init__.py
│   ├── cli.py           # Main CLI interface
│   ├── xtract.py        # PDF extraction
│   ├── ledgerfy.py      # Ledger conversion
│   └── config.json      # Default configuration
├── pyproject.toml
├── README.md
├── USAGE.md             # Detailed usage guide
└── LICENSE.txt
```

## Requirements

-   Python 3.8+
-   `pdfplumber` (for PDF extraction)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1.  Fork the repository.
2.  Create a feature branch.
3.  Make your changes.
4.  Add tests if applicable.
5.  Submit a pull request.

## License

This project is licensed under the MIT License - see the `LICENSE.txt` file for details.

## Support

If you encounter any issues or have questions, please file an issue on the GitHub repository.
