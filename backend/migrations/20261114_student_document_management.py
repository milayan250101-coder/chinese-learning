from pathlib import Path
from datetime import datetime
import sqlite3

from sqlalchemy import inspect

from backend import auth_models
from backend import student_profile_models
from backend.database import Base, engine


NEW_COLUMNS = {
    "folder_id": (
        "INTEGER REFERENCES student_note_folders(id) ON DELETE SET NULL"
    ),
    "document_type": (
        "VARCHAR(40) NOT NULL DEFAULT 'class_notes'"
    ),
    "source_mode": (
        "VARCHAR(40) NOT NULL DEFAULT 'local_file'"
    ),
    "storage_path": "VARCHAR(500)",
    "lesson_number": "INTEGER",
    "description": "TEXT",
    "pinyin_text": "TEXT",
    "translation_text": "TEXT",
}

FOLDER_COLUMNS = {
    "id", "student_id", "name", "level_name",
    "sort_order", "created_at",
}

PRESERVE_TABLES = [
    "student_notes",
    "knowledge_evidence",
    "analysis_jobs",
]


def main():
    print("========== 1. 数据库路径检查 ==========")

    database_path = engine.url.database
    if not database_path:
        raise RuntimeError("数据库路径为空。")

    actual_path = Path(database_path).resolve()
    expected_path = Path("chinese_learning.db").resolve()

    print("数据库：", actual_path)

    if actual_path != expected_path:
        raise RuntimeError(
            f"数据库路径不匹配：预期 {expected_path}"
        )

    if not actual_path.is_file():
        raise RuntimeError("数据库文件不存在，停止迁移。")

    print("\n========== 2. 创建未压缩数据库快照 ==========")

    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)

    backup_path = backup_dir / (
        "chinese_learning_before_student_documents_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
        + ".db"
    )

    with sqlite3.connect(str(actual_path)) as source:
        with sqlite3.connect(str(backup_path)) as target:
            source.backup(target)
            result = target.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

    if result != "ok":
        raise RuntimeError("数据库快照完整性检查失败。")

    print("快照已创建：", backup_path)

    print("\n========== 3. 检查模型和原有数据 ==========")

    if "student_note_folders" not in Base.metadata.tables:
        raise RuntimeError("资料文件夹模型未注册。")

    if "student_notes" not in Base.metadata.tables:
        raise RuntimeError("StudentNote 模型未注册。")

    with engine.connect() as conn:
        conn.exec_driver_sql("BEGIN IMMEDIATE")

        try:
            inspector = inspect(conn)
            tables = set(inspector.get_table_names())

            for required in ["students", "student_notes"]:
                if required not in tables:
                    raise RuntimeError(f"缺少原有数据表：{required}")

            before_counts = {}
            for table in PRESERVE_TABLES:
                if table in tables:
                    before_counts[table] = conn.exec_driver_sql(
                        f'SELECT COUNT(*) FROM "{table}"'
                    ).scalar_one()

            current_columns = {
                item["name"]
                for item in inspector.get_columns("student_notes")
            }

            present = set(NEW_COLUMNS).intersection(current_columns)

            if present and present != set(NEW_COLUMNS):
                raise RuntimeError(
                    "发现部分新字段已存在，迁移不完整。"
                    f"已存在字段：{sorted(present)}。"
                    "为避免误改，停止迁移。"
                )

            folder_exists = "student_note_folders" in tables

            if folder_exists:
                folder_columns = {
                    item["name"]
                    for item in inspector.get_columns(
                        "student_note_folders"
                    )
                }
                if not FOLDER_COLUMNS.issubset(folder_columns):
                    raise RuntimeError(
                        "资料文件夹表已存在但结构不完整，停止迁移。"
                    )

            print("原有数据数量：", before_counts)

            print("\n========== 4. 创建资料文件夹表 ==========")

            folder_table = Base.metadata.tables[
                "student_note_folders"
            ]

            Base.metadata.create_all(
                bind=conn,
                tables=[folder_table],
                checkfirst=True,
            )

            print("资料文件夹表检查完成。")

            print("\n========== 5. 增加资料管理字段 ==========")

            if not present:
                for column_name, definition in NEW_COLUMNS.items():
                    conn.exec_driver_sql(
                        f'ALTER TABLE student_notes '
                        f'ADD COLUMN "{column_name}" {definition}'
                    )
                    print("已增加：", column_name)
            else:
                print("资料管理字段已经完整存在，跳过重复添加。")

            print("\n========== 6. 验证数据和数据库 ==========")

            inspector = inspect(conn)
            final_columns = {
                item["name"]
                for item in inspector.get_columns("student_notes")
            }

            missing = set(NEW_COLUMNS) - final_columns
            if missing:
                raise RuntimeError(f"字段缺失：{sorted(missing)}")

            for table, expected_count in before_counts.items():
                actual_count = conn.exec_driver_sql(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).scalar_one()

                print(f"{table}: {actual_count}")

                if actual_count != expected_count:
                    raise RuntimeError(
                        f"{table} 数据数量发生变化，停止提交。"
                    )

            integrity = conn.exec_driver_sql(
                "PRAGMA integrity_check"
            ).scalar_one()

            if integrity != "ok":
                raise RuntimeError(
                    f"数据库完整性检查失败：{integrity}"
                )

            fk_errors = conn.exec_driver_sql(
                "PRAGMA foreign_key_check"
            ).fetchall()

            if fk_errors:
                raise RuntimeError(
                    f"发现外键错误：{fk_errors[:10]}"
                )

            conn.commit()

        except Exception:
            conn.rollback()
            raise

    print("\n迁移成功。")
    print("原有资料及关联记录数量保持不变。")
    print("数据库快照：", backup_path)


if __name__ == "__main__":
    main()
