#!/usr/bin/env python3
"""Initialize the eight root folders of the teacher's G grammar library.

Default mode is preview-only. Pass --apply to insert missing folders.
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import SessionLocal

# Register the users table in SQLAlchemy metadata before loading
# grammar models that reference ForeignKey("users.id").
from backend.auth_models import User
from backend.grammar.models import GrammarCategory

TEACHER_ID = 1

ROOT_CATEGORIES = [
    ("第一部分：词语类", 10),
    ("第二部分：补语类", 20),
    ("第三部分：句式类", 30),
    ("第四部分：复句类", 40),
    ("补充一", 50),
    ("补充二", 60),
    ("补充三", 70),
    ("补充四及后续扩展", 80),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually create missing categories. Without this flag, preview only.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        with db.begin():
            teacher_exists = db.execute(
                __import__("sqlalchemy").text(
                    "SELECT id FROM users WHERE id = :teacher_id"
                ),
                {"teacher_id": TEACHER_ID},
            ).first()

            if teacher_exists is None:
                raise RuntimeError(
                    f"教师用户 ID {TEACHER_ID} 不存在，停止初始化。"
                )

            to_create = []
            already_exists = []

            for name, sort_order in ROOT_CATEGORIES:
                existing = (
                    db.query(GrammarCategory)
                    .filter(
                        GrammarCategory.parent_id.is_(None),
                        GrammarCategory.name == name,
                        GrammarCategory.owner_teacher_id.in_(
                            [TEACHER_ID, None]
                        ),
                    )
                    .first()
                )

                if existing:
                    already_exists.append((name, existing.id))
                else:
                    to_create.append((name, sort_order))

            print("===== G 系列目录初始化预览 =====")
            print(f"教师用户 ID：{TEACHER_ID}")
            print(f"计划目录总数：{len(ROOT_CATEGORIES)}")
            print(f"已存在、将跳过：{len(already_exists)}")
            for name, category_id in already_exists:
                print(f"  跳过：{name}（ID {category_id}）")

            print(f"待创建：{len(to_create)}")
            for name, sort_order in to_create:
                print(f"  新建：{name}（排序 {sort_order}）")

            if not args.apply:
                print("\n预览模式：没有写入任何数据。")
                print("确认无误后，使用 --apply 执行创建。")
                return

            for name, sort_order in to_create:
                db.add(
                    GrammarCategory(
                        owner_teacher_id=TEACHER_ID,
                        parent_id=None,
                        name=name,
                        description="G 系列语法教学知识库目录",
                        sort_order=sort_order,
                        is_active=1,
                    )
                )

            db.flush()

            print("\n===== 初始化结果 =====")
            print(f"本次新建：{len(to_create)} 个目录")
            print("数据库事务即将提交。")

        print("事务已提交。")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
