"""Typed domain records and exact monetary input handling."""

import re
from dataclasses import dataclass
from enum import StrEnum

MAX_CENTS = 1_000_000_000_000


class BankError(Exception):
    """An expected validation or business-rule failure."""


class AccountStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class TransactionKind(StrEnum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER = "TRANSFER"


def parse_money(value: str) -> int:
    """Accept decimal rupees; never round or pass through floating point."""
    value = value.strip()
    match = re.fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", value)
    if match is None:
        raise BankError(
            "Use a nonnegative decimal amount with at most two places, e.g. 1250.50."
        )
    whole, _, fraction = value.partition(".")
    whole = whole.lstrip("0")
    if whole == "":
        whole = "0"
    if len(whole) > 11:
        raise BankError("Amount cannot exceed 10,000,000,000 rupees.")
    fraction = fraction.ljust(2, "0")
    rupees = int(whole)
    paise = int(fraction)
    cents = rupees * 100
    cents += paise
    if cents > MAX_CENTS:
        raise BankError("Amount cannot exceed 10,000,000,000 rupees.")
    if cents == 0:
        raise BankError("Amount must be greater than zero.")
    return cents


def money(cents: int) -> str:
    sign = ""
    if cents < 0:
        sign = "-"
    amount = abs(cents)
    rupees = amount // 100
    paise = amount % 100
    return f"{sign}{rupees:,}.{paise:02d}"


@dataclass(frozen=True, slots=True)
class Customer:
    id: int
    name: str
    email: str
    phone: str
    address: str
    created_at: str


@dataclass(frozen=True, slots=True)
class Account:
    id: int
    customer_id: int
    owner: str
    status: AccountStatus
    balance_cents: int
    opened_at: str


@dataclass(frozen=True, slots=True)
class StatementEntry:
    transaction_id: int
    created_at: str
    kind: TransactionKind
    counterparty_id: int | None
    change_cents: int
    balance_cents: int
