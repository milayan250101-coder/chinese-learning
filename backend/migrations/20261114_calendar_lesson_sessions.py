from pathlib import Path

from sqlalchemy import inspect

from backend import auth_models
from backend import student_profile_models
from backend.calendar import models as calendar_models
from backend import lesson_session_models
from backend.database import Base, engine


NEW_TABLES = [
    "calendar_connections",
    "calendar_external_calendars",
    "calendar_events",
    "calendar_event_sources",
    "calendar_sync_logs",
    "calendar_sync_conflicts",
    "lesson_sessions",
]

BASELINE_COUNTS = {
    "users": 1,
    "students": 2,
    "student_notes": 17,
    "student_vocab_progress": 141,
    "student_grammar_progress": 56,
    "knowledge_evidence": 233,
    "cl_course_progress": 1,
    "lesson_plans": 12,
}


def main():
    print("========== 1. 数据库路径检查 ==========")

    database_path = engine.url.database
    if not database_path:
        raise RuntimeError("数据库 URL 没有指定文件路径")

    actual_path = Path(database_path).resolve()
    expected_path = Path("chinese_learning.db").resolve()

    print("当前数据库：", actual_path)

    if actual_path != expected_path:
        raise RuntimeError(
            f"数据库路径不匹配：预期 {expected_path}"
        )

    print("\n========== 2. 检查模型注册 ==========")

    for name in NEW_TABLES:
        if name not in Base.metadata.tables:
            raise RuntimeError(f"模型没有注册：{name}")
        print("通过：", name)

    print("\n========== 3. 执行迁移 ==========")

    with engine.connect() as conn:
        # 在 SQLite 中先取得写锁，确保迁移操作处于同一事务。
        conn.exec_driver_sql("BEGIN IMMEDIATE")

        inspector = inspect(conn)
        existing_tables = set(inspector.get_table_names())

        students_columns = {
            column["name"]
            for column in inspector.get_columns("students")
        }

        existing_new_tables = existing_tables.intersection(NEW_TABLES)
        has_learning_started_at = (
            "learning_started_at" in students_columns
        )

        # 完整迁移后再次执行时，允许安全检查，不重复添加字段。
        if (
            len(existing_new_tables) == len(NEW_TABLES)
            and has_learning_started_at
        ):
            print("迁移结构已经完整存在，进行重复执行安全检查。")

        elif existing_new_tables or has_learning_started_at:
            raise RuntimeError(
                "发现部分迁移结构已经存在，但迁移尚不完整。"
                "为避免覆盖或误改数据库，停止执行。"
            )

        else:
            # 先添加学生学习开始时间。
            conn.exec_driver_sql(
                "ALTER TABLE students "
                "ADD COLUMN learning_started_at DATETIME"
            )
            print("已添加 students.learning_started_at")

            # 只创建本次指定的 7 张新表。
            tables = [
                Base.metadata.tables[name]
                for name in NEW_TABLES
            ]

            Base.metadata.create_all(
                bind=conn,
                tables=tables,
                checkfirst=True,
            )

            print("7 张新表及其模型定义已创建。")

        print("\n========== 4. 检查新表和字段 ==========")

        inspector = inspect(conn)
        current_tables = set(inspector.get_table_names())

        for name in NEW_TABLES:
            if name not in current_tables:
                raise RuntimeError(f"新表缺失：{name}")
            print("通过：", name)

        current_columns = {
            column["name"]
            for column in inspector.get_columns("students")
        }

        if "learning_started_at" not in current_columns:
            raise RuntimeError("learning_started_at 字段缺失")

        print("通过：students.learning_started_at")

        print("\n========== 5. 原有数据数量检查 ==========")

        for table_name, expected_count in BASELINE_COUNTS.items():
            actual_count = conn.exec_driver_sql(
                f'SELECT COUNT(*) FROM "{table_name}"'
            ).scalar_one()

            print(f"{table_name}: {actual_count}")

            if actual_count != expected_count:
                raise RuntimeError(
                    f"{table_name} 数量变化："
                    f"预期 {expected_count}，实际 {actual_count}"
                )

        print("\n========== 6. 数据库完整性检查 ==========")

        integrity = conn.exec_driver_sql(
            "PRAGMA integrity_check"
        ).scalar_one()

        print("integrity_check:", integrity)

        if integrity != "ok":
            raise RuntimeError("SQLite 完整性检查失败")

        foreign_key_errors = conn.exec_driver_sql(
            "PRAGMA foreign_key_check"
        ).fetchall()

        print("foreign_key_check:", foreign_key_errors)

        if foreign_key_errors:
            raise RuntimeError("发现外键错误")

        # 所有检查通过后才提交；此前任何异常都会回滚。
        conn.commit()

    print("\n迁移事务已成功提交。")
    print("原有核心数据数量保持不变。")


if __name__ == "__main__":
    main()
