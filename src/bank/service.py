"""Core banking operations; balance updates and history commit together."""

import re

from bank.db import Database, Row, integer, string
from bank.models import (
    MAX_CENTS,
    Account,
    AccountStatus,
    BankError,
    Customer,
    StatementEntry,
    TransactionKind,
)

CUSTOMER_QUERY = """
SELECT
    id,
    name,
    email,
    phone,
    address,
    created_at
FROM customers
"""

ACCOUNT_QUERY = """
SELECT
    a.id,
    a.customer_id,
    c.name,
    a.status,
    a.balance_cents,
    a.opened_at
FROM accounts AS a
JOIN customers AS c
    ON c.id = a.customer_id
"""


def text_field(value: str, label: str, limit: int) -> str:
    value = value.strip()
    message = f"{label} must contain 1-{limit} printable characters."
    if not value or len(value) > limit:
        raise BankError(message)
    for char in value:
        if ord(char) < 32:
            raise BankError(message)
    return value


def account_record(row: Row) -> Account:
    key = integer(row[0])
    customer = integer(row[1])
    owner = string(row[2])
    label = string(row[3])
    status = AccountStatus(label)
    balance = integer(row[4])
    opened = string(row[5])
    return Account(
        id=key,
        customer_id=customer,
        owner=owner,
        status=status,
        balance_cents=balance,
        opened_at=opened,
    )


def customer_record(row: Row) -> Customer:
    return Customer(
        id=integer(row[0]),
        name=string(row[1]),
        email=string(row[2]),
        phone=string(row[3]),
        address=string(row[4]),
        created_at=string(row[5]),
    )


class Bank:
    def __init__(self, database: Database) -> None:
        self.db: Database = database

    def customers(self) -> list[Customer]:
        clause = """
            ORDER BY id;
        """
        sql = CUSTOMER_QUERY + clause
        rows = self.db.rows(sql)
        customers: list[Customer] = []
        for row in rows:
            customer = customer_record(row)
            customers.append(customer)
        return customers

    def customer(self, key: int) -> Customer:
        clause = """
            WHERE id = ?;
        """
        sql = CUSTOMER_QUERY + clause
        rows = self.db.rows(sql, (key,))
        if not rows:
            raise BankError(f"Customer #{key} does not exist.")
        row = rows[0]
        return customer_record(row)

    def _add_customer(self, name: str, email: str, phone: str, address: str) -> int:
        name = text_field(name, "Name", 100)
        email = text_field(email, "Email", 254)
        email = email.lower()
        match = re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email)
        if match is None:
            raise BankError("Enter an email address such as student@example.com.")
        phone = text_field(phone, "Phone", 20)
        digits = re.sub(r"[ +()\-]", "", phone)
        if not digits.isascii() or not digits.isdigit() or not 7 <= len(digits) <= 15:
            raise BankError(
                "Phone must contain 7-15 digits, with optional +, spaces, (), or -."
            )
        address = text_field(address, "Address", 300)
        sql = """
            INSERT INTO customers (
                name,
                email,
                phone,
                address
            )
            VALUES (?, ?, ?, ?);
        """
        return self.db.insert(sql, (name, email, phone, address))

    def accounts(self) -> list[Account]:
        clause = """
            ORDER BY a.id;
        """
        sql = ACCOUNT_QUERY + clause
        rows = self.db.rows(sql)
        accounts: list[Account] = []
        for row in rows:
            account = account_record(row)
            accounts.append(account)
        return accounts

    def account(self, key: int) -> Account:
        clause = """
            WHERE a.id = ?;
        """
        sql = ACCOUNT_QUERY + clause
        rows = self.db.rows(sql, (key,))
        if not rows:
            raise BankError(f"Account #{key} does not exist.")
        row = rows[0]
        return account_record(row)

    def register(
        self, name: str, email: str, phone: str, address: str, cents: int
    ) -> Account:
        """Create a customer, account, and initial deposit in one transaction."""
        with self.db.atomic():
            return self._register(name, email, phone, address, cents)

    def _register(
        self, name: str, email: str, phone: str, address: str, cents: int
    ) -> Account:
        """Called within atomic(), including when creating sample data."""
        customer = self._add_customer(name, email, phone, address)
        sql = """
            INSERT INTO accounts (customer_id)
            VALUES (?);
        """
        key = self.db.insert(sql, (customer,))
        self._record(TransactionKind.DEPOSIT, None, key, cents)
        return self.account(key)

    def close_account(self, key: int) -> None:
        with self.db.atomic():
            account = self._active_account(key)
            if account.balance_cents != 0:
                raise BankError(
                    "Withdraw or transfer the entire balance before closing the account."
                )
            sql = """
                UPDATE accounts
                SET status = 'CLOSED'
                WHERE id = ?;
            """
            self.db.execute(sql, (key,))

    def _active_account(self, key: int) -> Account:
        account = self.account(key)
        if account.status != AccountStatus.ACTIVE:
            raise BankError(f"Account #{key} is closed.")
        return account

    def _record(
        self, kind: TransactionKind, source: int | None, target: int | None, cents: int
    ) -> int:
        """Called within atomic(): validate both accounts before changing either balance."""
        if not 1 <= cents <= MAX_CENTS:
            raise BankError("Amount must be positive and within the supported limit.")
        if source is not None:
            sender = self._active_account(source)
            if sender.balance_cents < cents:
                raise BankError("Insufficient funds.")
        if target is not None:
            receiver = self._active_account(target)
            balance = receiver.balance_cents + cents
            if balance > MAX_CENTS:
                raise BankError("Destination balance exceeds the supported limit.")
        if source is not None:
            sql = """
                UPDATE accounts
                SET balance_cents = balance_cents - ?
                WHERE id = ?;
            """
            self.db.execute(sql, (cents, source))
        if target is not None:
            sql = """
                UPDATE accounts
                SET balance_cents = balance_cents + ?
                WHERE id = ?;
            """
            self.db.execute(sql, (cents, target))
        sql = """
            INSERT INTO transactions (
                kind,
                source_account_id,
                target_account_id,
                amount_cents
            )
            VALUES (?, ?, ?, ?);
        """
        return self.db.insert(sql, (kind.value, source, target, cents))

    def deposit(self, key: int, cents: int) -> int:
        with self.db.atomic():
            return self._record(TransactionKind.DEPOSIT, None, key, cents)

    def withdraw(self, key: int, cents: int) -> int:
        with self.db.atomic():
            return self._record(TransactionKind.WITHDRAWAL, key, None, cents)

    def transfer(self, source: int, target: int, cents: int) -> int:
        if source == target:
            raise BankError("Source and destination accounts must be different.")
        with self.db.atomic():
            return self._record(TransactionKind.TRANSFER, source, target, cents)

    def statement(self, account: int) -> list[StatementEntry]:
        self.account(account)
        entries: list[StatementEntry] = []
        balance = 0
        sql = """
            SELECT
                id,
                created_at,
                kind,
                source_account_id,
                target_account_id,
                amount_cents
            FROM transactions
            WHERE source_account_id = ?
                OR target_account_id = ?
            ORDER BY id;
        """
        rows = self.db.rows(sql, (account, account))
        for row in rows:
            key = integer(row[0])
            created = string(row[1])
            label = string(row[2])
            kind = TransactionKind(label)
            amount = integer(row[5])

            if row[3] == account:
                other = row[4]
                change = -amount
            else:
                other = row[3]
                change = amount

            peer: int | None = None
            if other is not None:
                peer = integer(other)
            balance += change

            entry = StatementEntry(
                transaction_id=key,
                created_at=created,
                kind=kind,
                counterparty_id=peer,
                change_cents=change,
                balance_cents=balance,
            )
            entries.append(entry)
        return entries

    def seed_sample_data(self) -> bool:
        """Seed an empty database in a single transaction, preserving existing data."""
        with self.db.atomic():
            sql = """
                SELECT 1
                FROM customers
                LIMIT 1;
            """
            rows = self.db.rows(sql)
            if rows:
                return False
            sample = (
                (
                    "Aisha Rao",
                    "aisha@example.com",
                    "9876543210",
                    "Campus Road",
                    500_000,
                ),
                (
                    "Arjun Shah",
                    "arjun@example.com",
                    "9876543211",
                    "Lake Road",
                    300_000,
                ),
                (
                    "Meera Iyer",
                    "meera@example.com",
                    "9876543212",
                    "Market Road",
                    200_000,
                ),
            )
            keys: list[int] = []
            for name, email, phone, address, cents in sample:
                account = self._register(name, email, phone, address, cents)
                keys.append(account.id)

            aisha = keys[0]
            arjun = keys[1]
            meera = keys[2]
            self._record(TransactionKind.TRANSFER, aisha, arjun, 75_000)
            self._record(TransactionKind.WITHDRAWAL, arjun, None, 25_000)
            self._record(TransactionKind.DEPOSIT, None, meera, 50_000)
            return True
