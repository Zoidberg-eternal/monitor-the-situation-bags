CREATE TABLE IF NOT EXISTS token (
    token_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    creator_id      INTEGER NOT NULL,
    name            TEXT NOT NULL,
    ticker          TEXT NOT NULL UNIQUE,
    narrative       TEXT NOT NULL DEFAULT '',
    -- AMM pool reserves (constant-product: token_reserve * usd_reserve = k)
    token_reserve   REAL NOT NULL DEFAULT 1000000.0,
    usd_reserve     REAL NOT NULL DEFAULT 1000.0,
    total_supply    REAL NOT NULL DEFAULT 1000000.0,
    -- Creator fee accounting
    creator_fees_earned REAL NOT NULL DEFAULT 0.0,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (creator_id) REFERENCES user(user_id)
);
