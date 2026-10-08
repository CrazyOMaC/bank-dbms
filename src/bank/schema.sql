-- All money is integer paise (INR); timestamps are UTC.
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
        CHECK (length(trim(name)) BETWEEN 1 AND 100),
    email TEXT NOT NULL COLLATE NOCASE UNIQUE
        CHECK (length(email) BETWEEN 3 AND 254),
    phone TEXT NOT NULL
        CHECK (length(phone) BETWEEN 7 AND 20),
    address TEXT NOT NULL
        CHECK (length(trim(address)) BETWEEN 1 AND 300),
    created_at TEXT NOT NULL
        DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
) STRICT;

CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers (id),
    status TEXT NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'CLOSED')),
    balance_cents INTEGER NOT NULL DEFAULT 0
        CHECK (balance_cents BETWEEN 0 AND 1000000000000),
    opened_at TEXT NOT NULL
        DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (status <> 'CLOSED' OR balance_cents = 0)
) STRICT;

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL
        CHECK (kind IN ('DEPOSIT', 'WITHDRAWAL', 'TRANSFER')),
    source_account_id INTEGER REFERENCES accounts (id),
    target_account_id INTEGER REFERENCES accounts (id),
    amount_cents INTEGER NOT NULL
        CHECK (amount_cents BETWEEN 1 AND 1000000000000),
    created_at TEXT NOT NULL
        DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (
        (
            kind = 'DEPOSIT'
            AND source_account_id IS NULL
            AND target_account_id IS NOT NULL
        )
        OR (
            kind = 'WITHDRAWAL'
            AND source_account_id IS NOT NULL
            AND target_account_id IS NULL
        )
        OR (
            kind = 'TRANSFER'
            AND source_account_id IS NOT NULL
            AND target_account_id IS NOT NULL
            AND source_account_id <> target_account_id
        )
    )
) STRICT;

CREATE INDEX IF NOT EXISTS ix_accounts_customer
    ON accounts (customer_id);

CREATE INDEX IF NOT EXISTS ix_transactions_source
    ON transactions (source_account_id);

CREATE INDEX IF NOT EXISTS ix_transactions_target
    ON transactions (target_account_id);
