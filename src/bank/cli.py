"""A single interactive menu for the banking system."""

import argparse
import sqlite3
import sys
from collections.abc import Sequence
from pathlib import Path

from bank.db import Database
from bank.models import Account, BankError, Customer, money, parse_money
from bank.service import Bank


class Arguments(argparse.Namespace):
    db: Path | None


def table(headers: tuple[str, ...], rows: Sequence[tuple[str, ...]]) -> None:
    if not rows:
        print("No records found.")
        return
    widths: list[int] = []
    for index, header in enumerate(headers):
        width = len(header)
        for row in rows:
            size = len(row[index])
            width = max(width, size)
        width = min(width, 35)
        widths.append(width)

    def line(row: tuple[str, ...]) -> str:
        cells: list[str] = []
        for value, width in zip(row, widths, strict=True):
            if len(value) > width:
                size = width - 3
                value = value[:size] + "..."
            cell = value.ljust(width)
            cells.append(cell)
        return " | ".join(cells)

    heading = line(headers)
    print(heading)

    bars: list[str] = []
    for width in widths:
        bars.append("-" * width)
    divider = "-+-".join(bars)
    print(divider)

    for row in rows:
        text = line(row)
        print(text)


def ask_id(label: str) -> int:
    try:
        value = input(f"{label}: ").strip()
        key = int(value)
    except ValueError as error:
        raise BankError("ID must be a positive integer.") from error
    if key < 1:
        raise BankError("ID must be a positive integer.")
    return key


def show_account(account: Account, label: str) -> None:
    balance = money(account.balance_cents)
    print(f"\n{label}")
    print(f"Account ID: #{account.id}")
    print(f"Customer ID: #{account.customer_id}")
    print(f"Owner: {account.owner}")
    print(f"Status: {account.status.value}")
    print(f"Current balance: INR {balance}")
    print(f"Opened (UTC): {account.opened_at}")


def show_customer(customer: Customer) -> None:
    print("\nCustomer details")
    print(f"Customer ID: #{customer.id}")
    print(f"Name: {customer.name}")
    print(f"Email: {customer.email}")
    print(f"Phone: {customer.phone}")
    print(f"Address: {customer.address}")
    print(f"Registered (UTC): {customer.created_at}")


def show_accounts(bank: Bank) -> None:
    accounts = bank.accounts()
    rows: list[tuple[str, ...]] = []
    for account in accounts:
        row = (
            str(account.id),
            str(account.customer_id),
            account.owner,
            account.status.value,
            money(account.balance_cents),
        )
        rows.append(row)
    headers = ("Account", "Customer", "Owner", "Status", "Balance (INR)")
    table(headers, rows)


def show_customers(bank: Bank) -> None:
    customers = bank.customers()
    rows: list[tuple[str, ...]] = []
    for customer in customers:
        row = (
            str(customer.id),
            customer.name,
            customer.email,
            customer.phone,
            customer.address,
        )
        rows.append(row)
    headers = ("Customer", "Name", "Email", "Phone", "Address")
    table(headers, rows)


def show_statement(bank: Bank, key: int) -> None:
    entries = bank.statement(key)
    account = bank.account(key)
    show_account(account, "Account details")
    print("\nTransaction history")

    rows: list[tuple[str, ...]] = []
    for entry in entries:
        other = ""
        if entry.counterparty_id is not None:
            other = str(entry.counterparty_id)
        row = (
            str(entry.transaction_id),
            entry.created_at,
            entry.kind.value,
            other,
            money(entry.change_cents),
            money(entry.balance_cents),
        )
        rows.append(row)

    headers = (
        "Txn",
        "Timestamp (UTC)",
        "Kind",
        "Other account",
        "Change (INR)",
        "Balance (INR)",
    )
    table(headers, rows)


def handle_choice(bank: Bank, choice: str) -> None:
    match choice:
        case "1":
            name = input("Name: ")
            email = input("Email: ")
            phone = input("Phone: ")
            address = input("Address: ")
            value = input("Initial deposit (INR): ")
            cents = parse_money(value)
            account = bank.register(name, email, phone, address, cents)
            customer = bank.customer(account.customer_id)
            amount = money(cents)
            print(f"Registration successful. Initial deposit: INR {amount}.")
            show_customer(customer)
            show_account(account, "New account details")
        case "2":
            show_customers(bank)
        case "3":
            show_accounts(bank)
        case "4" | "5" | "6":
            label = "Account ID"
            if choice == "6":
                label = "Source account ID"
            source = ask_id(label)

            target: int | None = None
            if choice == "6":
                target = ask_id("Destination account ID")

            value = input("Amount (INR): ")
            cents = parse_money(value)
            if choice == "4":
                key = bank.deposit(source, cents)
                action = "Deposit"
            elif choice == "5":
                key = bank.withdraw(source, cents)
                action = "Withdrawal"
            else:
                if target is None:
                    raise BankError("A destination account is required.")
                key = bank.transfer(source, target, cents)
                action = "Transfer"
            amount = money(cents)
            print(f"{action} successful: INR {amount}. Transaction #{key}.")
            account = bank.account(source)
            if target is not None:
                show_account(account, "Source account after transfer")
                account = bank.account(target)
                show_account(account, "Destination account after transfer")
            else:
                show_account(account, "Updated account details")
        case "7":
            key = ask_id("Account ID")
            show_statement(bank, key)
        case "8":
            key = ask_id("Account ID")
            bank.close_account(key)
            print(f"Closed account #{key}; transaction history retained.")
            account = bank.account(key)
            show_account(account, "Closed account details")
        case _:
            print("Choose a listed menu number.")


def error_message(error: BankError | sqlite3.Error | OSError) -> str:
    message = str(error)
    if isinstance(error, sqlite3.IntegrityError) and "customers.email" in message:
        return "That email address is already registered."
    if isinstance(error, sqlite3.OperationalError) and "locked" in message:
        return "Database is busy. Retry after the other operation finishes."
    return message


def resume() -> bool:
    while True:
        choice = input("\nPress Enter to return to the menu, or 0 to exit: ").strip()
        if choice == "":
            return True
        if choice == "0":
            return False
        print("Press Enter to return to the menu, or enter 0 to exit.")


def menu(bank: Bank) -> None:
    while True:
        print(
            "\nBANKING AND ACCOUNT MANAGEMENT | INR\n"
            "  1. Register and open account\n"
            "  2. List customers\n"
            "  3. List accounts\n"
            "  4. Deposit\n"
            "  5. Withdraw\n"
            "  6. Transfer\n"
            "  7. Account statement\n"
            "  8. Close account (zero balance required)\n"
            "  0. Exit"
        )
        try:
            choice = input("Choose: ").strip()
            if choice == "0":
                return
            try:
                handle_choice(bank, choice)
            except (BankError, sqlite3.Error, OSError) as error:
                message = error_message(error)
                print(f"Error: {message}", file=sys.stderr)
            if not resume():
                return
        except EOFError, KeyboardInterrupt:
            print("\nGoodbye.")
            return


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="bank", description="Banking and Account Management - interactive CLI"
    )
    parser.add_argument(
        "--db", type=Path, help="SQLite database path (default: data/bank.sqlite3)"
    )
    args = Arguments()
    parser.parse_args(namespace=args)
    path = args.db
    if path is None:
        path = Path("data/bank.sqlite3")
    try:
        with Database(path) as database:
            bank = Bank(database)
            seeded = bank.seed_sample_data()
            if seeded:
                print("Added sample customers, accounts, and transactions.")
            print(f"Database: {path.resolve()}")
            menu(bank)
    except (BankError, sqlite3.Error, OSError) as error:
        message = error_message(error)
        print(f"Error: {message}", file=sys.stderr)
        raise SystemExit(1) from error
    except EOFError, KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        raise SystemExit(130) from None
