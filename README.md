# Banking and Account Management System

A small college DBMS project: one interactive CLI, three SQLite tables, and strictly typed Python. It uses only the Python standard library at runtime.

## Start

Requires Python **3.14+** and uv. Run these from the project directory:

```powershell
uv sync
uv run bank
```

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
