# Bank Transaction Monitoring — Odoo 18 Module

An Odoo module that automates bank transaction monitoring for compliance by running periodic background checks to flag suspicious activity.

---

## Features

- Flags transactions of ₦10,000,000 or more for review
- Detects customers who make more than 5 transactions within a 10-minute window
- Processes normal transactions automatically via a scheduled cron job
- Prevents duplicate processing using state-based transaction lifecycle
- Handles errors per transaction without aborting the entire batch

---

## Module Structure

```
bank_transaction_monitoring/
├── __init__.py
├── __manifest__.py
├── data/
│   └── scheduled_action.xml       # Cron job + sequence definition
├── models/
│   ├── __init__.py
│   └── bank_transaction.py        # Core model and business logic
├── security/
│   └── ir.model.access.csv        # Access rights
└── views/
    └── bank_transaction_view.xml  # List, form, and search views
```

---

## Installation

### Prerequisites
- Odoo 18
- PostgreSQL 16+

### Steps

1. Clone the repository into your custom addons folder:
   ```bash
   git clone https://github.com/....
   ```

2. Add the project path to `addons_path` in `odoo.conf`:
   ```ini
   addons_path = c:\program files\odoo 18.0.20261026\server\odoo\addons,c:\path\to\NewProject
   ```

3. Restart the Odoo service.

4. In Odoo, go to **Settings → Activate Developer Mode**.

5. Go to **Apps → Update Apps List**.

6. Search for `Bank Transaction Monitoring` and click **Install**.

---

## Configuration

The following thresholds are defined as constants in `models/bank_transaction.py` and can be adjusted as needed:

| Constant | Default | Description |
|---|---|---|
| `LARGE_AMOUNT_THRESHOLD` | `10,000,000` | Minimum amount (₦) to flag a transaction |
| `RAPID_TX_LIMIT` | `5` | Max transactions allowed per customer within the time window |
| `RAPID_TX_WINDOW` | `10` | Rolling time window in minutes for rapid transaction detection |

---

## How It Works

### Transaction Lifecycle

```
[Created] → pending → processed
                    → flagged
```

Every transaction starts as `pending`. The cron job picks up all pending transactions and evaluates each one:

- If the amount is ≥ ₦10,000,000 → flagged
- If the customer has > 5 transactions in the last 10 minutes → flagged
- Otherwise → processed

A transaction can only be processed once because the cron exclusively queries `state = pending`.

### Scheduled Action

The cron job runs every **1 minute** and calls `process_transactions()` on the `bank.transaction` model.

---

## Design Decisions

**Duplicate processing prevention**
The `state` field acts as a processing lock. Once a transaction moves out of `pending`, the cron will never touch it again. A `unique(name)` SQL constraint also prevents duplicate records at the database level.

**Performance**
- Rapid transaction detection uses a single aggregated SQL query across all pending customers before the processing loop — avoiding N+1 queries.
- `index=True` is set on `customer_id`, `transaction_date`, and `state` to speed up cron queries on large datasets.

**Error isolation**
Each transaction is processed inside a `try/except` block so a single bad record never aborts the entire batch. Errors are logged with full tracebacks via Python's `logging` module.

**Flag reason transparency**
When a transaction is flagged, the specific reason(s) are written to the `flag_reason` field so compliance officers can see exactly why it was flagged.

---

## Access Rights

| Group | Read | Write | Create | Delete |
|---|---|---|---|---|
| Internal User | ✅ | ✅ | ✅ | ❌ |
| System Admin | ✅ | ✅ | ✅ | ✅ |

---

## Usage

1. Navigate to **Transaction Monitoring → Transactions**
2. Create a new transaction with a customer, amount, and date
3. The cron job will automatically process it within 1 minute
4. Flagged transactions appear highlighted in red in the list view
5. Open a flagged transaction to see the `Flag Reason` detail

---

## License

LGPL-3
