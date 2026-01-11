# Ledgerfy - Configuration Guide

This guide explains how to configure the `ledgerfy` command using a JSON configuration file to categorize M-Pesa transactions. It covers advanced features for precise transaction matching.

## Configuration Structure

The configuration file is a JSON object with the following structure:

```json
{
  "accounts": ["list", "of", "valid", "accounts"],
  "rules": [
    {
      "keywords": ["keyword1", "keyword2"],
      "match_type": "any",  // or "all"
      "condition": "amount > 1000",
      "exclude": ["badword1", "badword2"],
      "account": "Expenses:Category:Subcategory"
    }
  ],
  "default_account": "Expenses:Uncategorized"
}
```

## Rule Processing Order

Rules are processed from top-to-bottom. The first matching rule takes precedence. This allows for:

-   Placing specific rules before general rules.
-   Creating fallback rules.
-   Handling edge cases with precise rules first.

## Keywords Matching

### Basic Keyword Matching (OR logic)

By default, rules use `OR` logic (`"match_type": "any"`):

```json
{
  "keywords": ["airtime", "data", "recharge"],
  "account": "Expenses:Airtime"
}
```
Matches if the transaction description contains *ANY* of the specified keywords.

### AND Logic Matching

Use `"match_type": "all"` for `AND` logic:

```json
{
  "keywords": ["traffic", "fine", "paid"],
  "match_type": "all",
  "account": "Expenses:Taxes:Fines"
}
```
Only matches if the transaction description contains *ALL* specified keywords.

## Condition Field

The `condition` field allows for amount-based logic using Python expressions.

### Basic Amount Conditions

```json
{
  "keywords": ["jane", "doe"],
  "condition": "amount >= 1000",
  "account": "Expenses:Others:Doe"
},
{
  "keywords": ["jane", "doe"],
  "account": "Expenses:Personal:Food"
}
```
How it works:

-   If `amount >= 1000` AND contains "jane" or "doe" → `Expenses:Others:Doe`
-   If `amount < 1000` AND contains "jane" or "doe" → `Expenses:Personal:Food`

### Available Variables in Conditions

-   `amount`: The transaction amount (positive for expenses, negative for income).

You can also use mathematical operations and comparisons (e.g., `>`, `<`, `>=`, `<=`, `==`, `!=`, `and`, `or`, `not`).

### Complex Conditions

```json
{
  "keywords": ["bonus"],
  "condition": "amount > 5000 and amount < 10000",
  "account": "Income:Bonus:Medium"
},
{
  "keywords": ["bonus"],
  "condition": "amount >= 10000",
  "account": "Income:Bonus:Large"
}
```

## Exclude Field

The `exclude` field acts as a veto: if any exclude keyword matches, the rule will *not* be applied, even if other conditions are met.

### Exclude with ANY Logic (Default `match_type`)

```json
{
  "keywords": ["airtime", "data", "recharge"],
  "match_type": "any",
  "exclude": ["free", "bonus", "promo"],
  "account": "Expenses:Airtime"
}
```
Behavior:

-   ✅ "Airtime purchase" → Matches (has keyword, no exclude)
-   ❌ "Free airtime" → Fails (has keyword BUT also has exclude word)
-   ❌ "Bonus data" → Fails (has keyword BUT also has exclude word)

### Exclude with ALL Logic

```json
{
  "keywords": ["traffic", "fine", "paid"],
  "match_type": "all",
  "exclude": ["warning", "notice"],
  "account": "Expenses:Taxes:Fines"
}
```
Behavior:

-   ✅ "Paid traffic fine" → Matches (ALL keywords, no exclude)
-   ❌ "Paid traffic fine notice" → Fails (ALL keywords BUT has exclude word)

## Advanced Matching Examples

### 1. Multi-Level Categorization

```json
{
  "keywords": ["uber", "bolt", "taxi"],
  "match_type": "any",
  "condition": "amount < 500",
  "account": "Expenses:Transport:Local"
},
{
  "keywords": ["uber", "bolt", "taxi"],
  "match_type": "any",
  "condition": "amount >= 500",
  "account": "Expenses:Transport:LongDistance"
}
```

### 2. Business vs Personal Transactions

```json
{
  "keywords": ["consulting", "invoice", "payment"],
  "match_type": "all",
  "exclude": ["friend", "family", "gift"],
  "account": "Income:Business:Consulting"
},
{
  "keywords": ["consulting", "payment"],
  "match_type": "all",
  "account": "Income:Personal:Consulting"
}
```

### 3. Specific vs General Rules

```json
{
  "keywords": ["shell", "premium", "fuel"],
  "match_type": "all",
  "account": "Expenses:Transport:Fuel:Premium"
},
{
  "keywords": ["shell", "fuel"],
  "match_type": "any",
  "account": "Expenses:Transport:Fuel:Regular"
}
```

## Practical Configuration Examples

### Complete Example Config

```json
{
  "accounts": [
    "Income:Salary",
    "Income:Bonus",
    "Expenses:Food:Dining",
    "Expenses:Food:Groceries",
    "Expenses:Transport:Fuel",
    "Expenses:Transport:Taxi",
    "Expenses:Utilities:Electricity",
    "Expenses:Entertainment",
    "Assets:Checking:Cash",
    "Expenses:MpesaCharges"
  ],
  "rules": [
    // Salary - specific keywords, no conditions needed
    {
      "keywords": ["salary", "payroll"],
      "account": "Income:Salary"
    },

    // Large bonuses go to separate account
    {
      "keywords": ["bonus"],
      "condition": "amount >= 10000",
      "account": "Income:Bonus:Large"
    },

    // Regular bonuses
    {
      "keywords": ["bonus"],
      "account": "Income:Bonus"
    },

    // Dining vs groceries based on keywords
    {
      "keywords": ["restaurant", "cafe", "hotel"],
      "match_type": "any",
      "account": "Expenses:Food:Dining"
    },
    {
      "keywords": ["naivas", "quickmart", "supermarket"],
      "match_type": "any",
      "account": "Expenses:Food:Groceries"
    },

    // Fuel purchases with premium detection
    {
      "keywords": ["shell", "v-power", "premium"],
      "match_type": "all",
      "account": "Expenses:Transport:Fuel:Premium"
    },
    {
      "keywords": ["shell", "fuel"],
      "match_type": "any",
      "account": "Expenses:Transport:Fuel:Regular"
    },

    // Cash withdrawals without charges
    {
      "keywords": ["withdrawal", "agent"],
      "match_type": "all",
      "exclude": ["charge", "fee"],
      "account": "Assets:Checking:Cash"
    },

    // M-Pesa charges
    {
      "keywords": ["charge", "withdrawal"],
      "match_type": "any",
      "account": "Expenses:MpesaCharges"
    }
  ],
  "default_account": "Expenses:Uncategorized"
}
```

## Best Practices

-   **Order Matters:** Place specific rules before general ones.
-   **Use Conditions Wisely:** Combine with keywords for precise matching.
-   **Test Your Rules:** Use small test files to verify categorization.
-   **Document Complex Rules:** Add comments in JSON using dummy fields or external documentation if needed.
-   **Regular Updates:** Review and update rules as your spending patterns change.

## Debugging Tips

-   **Check Rule Order:** Rules are processed top-down.
-   **Verify Keywords:** Matching is case-insensitive; check for typos.
-   **Test Conditions:** Use sample transactions to test condition logic.
-   **Watch for Excludes:** Exclude words can silently veto matches.
-   **Use Default Account:** All unmatched transactions will go to the default account.

## Common Patterns

### Pattern 1: Amount-Based Tiers

```json
{
  "keywords": ["x"],
  "condition": "amount < 100",
  "account": "A"
},
{
  "keywords": ["x"],
  "condition": "amount < 500",
  "account": "B"
},
{
  "keywords": ["x"],
  "account": "C"}
```

### Pattern 2: Specificity Cascade

```json
{
  "keywords": ["a", "b"],
  "match_type": "all",
  "account": "Specific"
},
{
  "keywords": ["a"],
  "account": "General"}
```

### Pattern 3: Exclusion Filtering

```json
{
  "keywords": ["service"],
  "exclude": ["free"],
  "account": "PaidService"
},
{
  "keywords": ["free", "service"],
  "account": "FreeService"}
```

## Troubleshooting

### Problem: Rule not matching expected transactions

-   **Check:** Keywords are spelled correctly and in lowercase.
-   **Check:** No exclude words are accidentally matching.
-   **Check:** Condition logic matches the amount values.
-   **Check:** Rule order isn't being overridden by earlier rules.

### Problem: Too many transactions going to default

-   **Check:** Rules cover common transaction types.
-   **Check:** Keywords are broad enough to match variations.
-   **Check:** `match_type` is appropriate (`any` vs `all`).

### Problem: Incorrect categorization

-   **Check:** More specific rules are placed before general ones.
-   **Check:** Conditions account for negative amounts (income) vs positive (expenses).
-   **Check:** Amounts are being parsed correctly from source data.
