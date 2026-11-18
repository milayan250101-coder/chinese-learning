from pathlib import Path
from datetime import datetime
import sqlite3


NEW_COLUMNS = {
    "link_url": "VARCHAR(2000)",
    "link_provider": "VARCHAR(100)",
    "link_title": "VARCHAR(255)",
    "external_file_id": "VARCHAR(500)",
    "original_file_deleted_at": "DATETIME",
}


def main():
    db_path = Path("chinese_learning.db").resolve()
    if not db_path.is_file():
        raise RuntimeError(f"找不到数据库：{db_path}")

    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    backup_path = backup_dir / (
        "chinese_learning_before_document_sources_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
        + ".db"
    )

    with sqlite3.connect(str(db_path)) as source:
        with sqlite3.connect(str(backup_path)) as target:
            source.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("数据库快照完整性检查失败。")

    print("数据库快照：", backup_path)

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("BEGIN IMMEDIATE")
        try:
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if "student_notes" not in tables:
                raise RuntimeError("缺少 student_notes 表。")

            before = {
                name: conn.execute(
                    f'SELECT COUNT(*) FROM "{name}"'
                ).fetchone()[0]
                for name in ("student_notes", "knowledge_evidence", "analysis_jobs")
                if name in tables
            }

            columns = {
                row[1] for row in conn.execute(
                    "PRAGMA table_info(student_notes)"
                )
            }

            for name, definition in NEW_COLUMNS.items():
                if name not in columns:
                    conn.execute(
                        f'ALTER TABLE student_notes ADD COLUMN "{name}" {definition}'
                    )
                    print("新增字段：", name)
                else:
                    print("字段已存在：", name)

            after = {
                name: conn.execute(
                    f'SELECT COUNT(*) FROM "{name}"'
                ).fetchone()[0]
                for name in before
            }
            if before != after:
                raise RuntimeError(f"原有资料或关联记录数量变化：{before} -> {after}")

            if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("数据库完整性检查失败。")
            fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
            if fk_errors:
                raise RuntimeError(f"外键检查失败：{fk_errors[:10]}")

            conn.commit()
            print("迁移成功，原有数据数量保持不变：", after)
        except Exception:
            conn.rollback()
            raise


if __name__ == "__main__":
    main()
