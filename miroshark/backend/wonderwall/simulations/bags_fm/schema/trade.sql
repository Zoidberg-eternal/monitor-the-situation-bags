CREATE TABLE IF NOT EXISTS trade (
    trade_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    token_id    INTEGER NOT NULL,
    side        TEXT NOT NULL,       -- 'buy' or 'sell'
    tokens      REAL NOT NULL,
    price       REAL NOT NULL,       -- effective price per token
    cost        REAL NOT NULL,       -- total USD cost (negative for sells)
    creator_fee REAL NOT NULL DEFAULT 0.0,
    created_at  TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user(user_id),
    FOREIGN KEY (token_id) REFERENCES token(token_id)
);
