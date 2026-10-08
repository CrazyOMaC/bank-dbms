-- Read-only examples for a viva or SQLite database browser.
PRAGMA foreign_keys = ON;

-- Accounts with their owners (one-to-many join).
SELECT
    a.id AS account_id,
    c.name AS owner,
    a.status,
    a.balance_cents
FROM accounts AS a
JOIN customers AS c
    ON c.id = a.customer_id
ORDER BY a.id;

-- Account counts per customer.
SELECT
    c.id,
    c.name,
    COUNT(a.id) AS account_count
FROM customers AS c
LEFT JOIN accounts AS a
    ON a.customer_id = c.id
GROUP BY c.id
ORDER BY c.id;

-- Transactions involving account #1, ordered chronologically by ID.
SELECT
    id,
    created_at,
    kind,
    source_account_id,
    target_account_id,
    amount_cents
FROM transactions
WHERE source_account_id = 1
    OR target_account_id = 1
ORDER BY id;

-- Compare stored balances with transaction history. This should return no rows.
SELECT
    a.id,
    a.balance_cents
FROM accounts AS a
WHERE a.balance_cents <> (
    SELECT
        COALESCE(
            SUM(
                CASE
                    WHEN t.target_account_id = a.id THEN t.amount_cents
                    ELSE -t.amount_cents
                END
            ),
            0
        )
    FROM transactions AS t
    WHERE t.source_account_id = a.id
        OR t.target_account_id = a.id
);

PRAGMA foreign_key_check;
PRAGMA integrity_check;
