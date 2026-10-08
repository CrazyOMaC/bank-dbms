# Banking and Account Management System

A small college DBMS project: one interactive CLI, three SQLite tables, and strictly typed Python. It uses only the Python standard library at runtime.

## Start

Requires Python **3.14+** and uv. Run these from the project directory:

```powershell
uv sync
uv run bank
```

Startup creates `data/bank.sqlite3` and seeds three customers, three accounts, and six transactions if the database is empty. Each account belongs to one customer. Later runs preserve your changes and do not duplicate the sample data. Use a new filename to start fresh with sample data:

```powershell
uv run bank --db data/fresh-bank.sqlite3
```

All operations use the menu. After the first installation, the application works offline. `uv sync --no-dev` installs only the application.

## Menu

| Option | Operation |
| --- | --- |
| 1 | Register a customer and open an account with an initial deposit |
| 2 | List customers |
| 3 | List accounts, their owners, and balances |
| 4 | Deposit money |
| 5 | Withdraw money |
| 6 | Transfer money between two accounts |
| 7 | Show an account's transaction history and running balance |
| 8 | Close an account after its balance reaches zero |
| 0 | Exit |

Registration asks for name, email, phone, address, and a positive initial deposit, then shows the saved customer and account details. The deposit appears as the first transaction on the account's statement. Customer creation, account creation, and the initial deposit all succeed together or roll back together.

Deposits and withdrawals show the amount, transaction ID, and affected account's details with its updated balance. Transfers show both the source and destination accounts, including their owners and updated balances. Closure shows the account's closed status and zero balance. Account details also include the customer ID and opening timestamp.

After each choice, the result stays visible while the app asks you to **press Enter to return to the menu, or enter 0 to exit**. Errors also pause at this prompt. Ctrl+C or end-of-input exits; on Windows, end-of-input is Ctrl+Z followed by Enter.

## Five-minute demonstration

Press Enter at the prompt after each operation to return to the menu.

1. Start `uv run bank`. Choose **2** to list customers, then **3** to list accounts.
2. Choose **6**: source account `1`, destination account `2`, amount `100.50`. The result shows both accounts and their updated balances immediately.
3. Choose **5**: account `1`, amount `999999`. This fails with "Insufficient funds." Choose **3** to show the balances stayed unchanged.
4. Choose **7** for account `1` to show the transaction history and running balance.
5. Choose **1** to register a new customer with an initial deposit of `500`. Use the printed account ID with **7** to show the opening deposit. Choose **5** to withdraw `500`, then **8** to close that account.
6. Open [the ER diagram](docs/er-diagram.svg) and explain the customer-to-account relationship and the two account references on a transfer.

Fresh sample balances:

| Account | Owner | Balance (INR) |
| --- | --- | ---: |
| 1 | Aisha Rao | 4,250.00 |
| 2 | Arjun Shah | 3,500.00 |
| 3 | Meera Iyer | 2,500.00 |

## Database design

- [Detailed ER diagram (SVG)](docs/er-diagram.svg): 25 nodes showing stored and derived attributes, relationship diamonds, keys, and participation/cardinality labels; open in a browser or insert into slides.
- [Mermaid ER diagram and design notes](docs/er-diagram.md).
- [SQLite schema](src/bank/schema.sql).
- [Example SQL queries](docs/queries.sql) for your viva.

`customers` stores contact details. `accounts` stores a single owner, status, and balance. `transactions` stores deposits, withdrawals, and transfers. A transfer is one transaction with a source account and destination account.

Money is integer paise, displayed in INR. Enter amounts such as `100`, `100.5`, or `100.50`. Negative values, zero, extra decimal places, and scientific notation are rejected. Account balances and transaction amounts are limited to INR 10,000,000,000.00.

SQLite enforces foreign keys, unique customer emails, nonnegative balances, account statuses, and valid transaction shapes. The service uses `BEGIN IMMEDIATE` to create a customer and account with an initial deposit atomically. It also validates funds, updates balances, and inserts transaction history atomically for later banking operations. Failed operations roll back. Opening balances are recorded as deposit transactions, so statements include the initial deposit when calculating running balances. Closing an account retains its history and prevents further transactions through the app.

## Source and typing

```text
src/bank/
  cli.py       interactive menu and display
  models.py    typed records, enums, exact money parsing
  db.py        SQLite connection and atomic transactions
  service.py   customer, account, and transaction operations
  schema.sql   three tables, constraints, and indexes
docs/
  er-diagram.svg
  er-diagram.md
  queries.sql
```

All functions are annotated. Domain records are immutable dataclasses, statuses and transaction kinds are enums, and database rows are validated before becoming typed records. Pyrefly uses its strict preset.

```powershell
uv run pyrefly check
uv run ruff check src
uv run ruff format --check src
```

No tests are included, as requested. Verification uses these static checks and manual menu workflows.

This version uses schema version 2. If opening an older database with a different schema, supply a new filename with `--db`.
