import sqlite3
from pathlib import Path
from datetime import datetime


DB = Path("chinese_learning.db").resolve()

TABLES = {
    "student_vocab_progress": {
        "columns": """
            id, student_id, vocabulary_number, syllabus_version,
            learning_status, review_status, first_seen_at,
            last_seen_at, occurrence_count, reviewed_by_user_id,
            reviewed_at, teacher_comment, created_at, updated_at
        """,
        "create": """
            CREATE TABLE student_vocab_progress_new (
                id INTEGER NOT NULL PRIMARY KEY,
                student_id INTEGER NOT NULL,
                vocabulary_number INTEGER NOT NULL,
                syllabus_version VARCHAR(20) NOT NULL,
                learning_status VARCHAR(30) NOT NULL,
                review_status VARCHAR(30) NOT NULL,
                first_seen_at DATETIME,
                last_seen_at DATETIME,
                occurrence_count INTEGER NOT NULL,
                reviewed_by_user_id INTEGER,
                reviewed_at DATETIME,
                teacher_comment TEXT,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                CONSTRAINT uq_student_vocabulary_progress
                    UNIQUE (student_id, vocabulary_number),
                CONSTRAINT ck_student_vocab_learning_status
                    CHECK (learning_status IN
                    ('not_seen','exposed','learned','mastered','review')),
                CONSTRAINT ck_student_vocab_review_status
                    CHECK (review_status IN
                    ('pending','approved','rejected')),
                FOREIGN KEY(student_id) REFERENCES students(id)
                    ON DELETE CASCADE,
                FOREIGN KEY(vocabulary_number)
                    REFERENCES hsk_vocabulary(number)
                    ON DELETE RESTRICT,
                FOREIGN KEY(reviewed_by_user_id) REFERENCES users(id)
                    ON DELETE SET NULL
            )
        """,
        "indexes": [
            "CREATE INDEX ix_student_vocab_progress_id "
            "ON student_vocab_progress(id)",
            "CREATE INDEX ix_student_vocab_student_status "
            "ON student_vocab_progress(student_id, learning_status)",
        ],
    },
    "student_grammar_progress": {
        "columns": """
            id, student_id, grammar_point_id, syllabus_version,
            learning_status, review_status, first_seen_at,
            last_seen_at, occurrence_count, reviewed_by_user_id,
            reviewed_at, teacher_comment, created_at, updated_at
        """,
        "create": """
            CREATE TABLE student_grammar_progress_new (
                id INTEGER NOT NULL PRIMARY KEY,
                student_id INTEGER NOT NULL,
                grammar_point_id INTEGER NOT NULL,
                syllabus_version VARCHAR(20) NOT NULL,
                learning_status VARCHAR(30) NOT NULL,
                review_status VARCHAR(30) NOT NULL,
                first_seen_at DATETIME,
                last_seen_at DATETIME,
                occurrence_count INTEGER NOT NULL,
                reviewed_by_user_id INTEGER,
                reviewed_at DATETIME,
                teacher_comment TEXT,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                CONSTRAINT uq_student_grammar_progress
                    UNIQUE (student_id, grammar_point_id, syllabus_version),
                CONSTRAINT ck_student_grammar_learning_status
                    CHECK (learning_status IN
                    ('not_seen','exposed','learned','mastered','review')),
                CONSTRAINT ck_student_grammar_review_status
                    CHECK (review_status IN
                    ('pending','approved','rejected')),
                FOREIGN KEY(student_id) REFERENCES students(id)
                    ON DELETE CASCADE,
                FOREIGN KEY(grammar_point_id)
                    REFERENCES hsk_grammar_points(id)
                    ON DELETE RESTRICT,
                FOREIGN KEY(reviewed_by_user_id) REFERENCES users(id)
                    ON DELETE SET NULL
            )
        """,
        "indexes": [
            "CREATE INDEX ix_student_grammar_progress_id "
            "ON student_grammar_progress(id)",
            "CREATE INDEX ix_student_grammar_student_status "
            "ON student_grammar_progress(student_id, learning_status)",
        ],
    },
}


def main():
    if not DB.is_file():
        raise RuntimeError(f"数据库不存在：{DB}")

    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)

    backup = backup_dir / (
        "chinese_learning_before_hsk_status_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
        + ".db"
    )

    print("数据库：", DB)

    # 创建独立数据库快照
    with sqlite3.connect(str(DB)) as source:
        with sqlite3.connect(str(backup)) as target:
            source.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("备份完整性检查失败")

    print("备份：", backup)

    conn = sqlite3.connect(str(DB))
    conn.execute("PRAGMA foreign_keys=OFF")

    try:
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

        for table in TABLES:
            if table not in tables:
                raise RuntimeError(f"缺少数据表：{table}")

            inbound = []
            for (other,) in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ):
                if other == table:
                    continue
                for fk in conn.execute(
                    f'PRAGMA foreign_key_list("{other}")'
                ):
                    if fk[2] == table:
                        inbound.append(other)

            if inbound:
                raise RuntimeError(
                    f"{table} 出现新的外部引用：{inbound}"
                )

        conn.execute("BEGIN IMMEDIATE")

        before = {}

        for table, config in TABLES.items():
            before[table] = conn.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]

            conn.execute(config["create"])

            columns = config["columns"]
            conn.execute(
                f'INSERT INTO "{table}_new" ({columns}) '
                f'SELECT {columns} FROM "{table}"'
            )

            copied = conn.execute(
                f'SELECT COUNT(*) FROM "{table}_new"'
            ).fetchone()[0]

            if copied != before[table]:
                raise RuntimeError(f"{table} 复制数量不一致")

            conn.execute(f'DROP TABLE "{table}"')
            conn.execute(
                f'ALTER TABLE "{table}_new" RENAME TO "{table}"'
            )

            for index_sql in config["indexes"]:
                conn.execute(index_sql)

        print("\n迁移前后记录数量：")
        for table in TABLES:
            after = conn.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]

            print(table, before[table], "->", after)

            if before[table] != after:
                raise RuntimeError(f"{table} 数据数量发生变化")

        integrity = conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity != "ok":
            raise RuntimeError(f"数据库完整性错误：{integrity}")

        fk_errors = conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if fk_errors:
            raise RuntimeError(f"外键检查失败：{fk_errors[:10]}")

        conn.commit()
        print("\n迁移成功！")

    except Exception:
        conn.rollback()
        print("\n迁移失败，事务已回滚。")
        raise

    finally:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.close()


if __name__ == "__main__":
    main()
