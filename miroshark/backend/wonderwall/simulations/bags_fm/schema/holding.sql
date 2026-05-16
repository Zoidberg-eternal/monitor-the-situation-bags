CREATE TABLE IF NOT EXISTS holding (
    holding_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    token_id    INTEGER NOT NULL,
    amount      REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY (user_id) REFERENCES user(user_id),
    FOREIGN KEY (token_id) REFERENCES token(token_id),
    UNIQUE(user_id, token_id)
);
