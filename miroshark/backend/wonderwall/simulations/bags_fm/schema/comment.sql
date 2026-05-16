CREATE TABLE IF NOT EXISTS token_comment (
    comment_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    token_id    INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    FOREIGN KEY (token_id) REFERENCES token(token_id),
    FOREIGN KEY (user_id) REFERENCES user(user_id)
);
