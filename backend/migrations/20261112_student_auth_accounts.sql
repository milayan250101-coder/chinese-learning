-- Student independent login accounts
-- Existing students and teacher data are not modified.

BEGIN IMMEDIATE;

CREATE TABLE student_auth_accounts (
    id INTEGER NOT NULL PRIMARY KEY,
    student_id INTEGER NOT NULL,
    login_username VARCHAR(100) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL,
    must_change_password BOOLEAN NOT NULL,
    last_login_at DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT uq_student_auth_account_student UNIQUE (student_id),
    FOREIGN KEY(student_id)
        REFERENCES students (id)
        ON DELETE CASCADE
);

CREATE INDEX ix_student_auth_account_active
    ON student_auth_accounts (is_active);

CREATE INDEX ix_student_auth_accounts_id
    ON student_auth_accounts (id);

CREATE UNIQUE INDEX ix_student_auth_accounts_login_username
    ON student_auth_accounts (login_username);

CREATE INDEX ix_student_auth_accounts_student_id
    ON student_auth_accounts (student_id);

COMMIT;
