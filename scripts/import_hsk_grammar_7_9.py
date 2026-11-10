import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from backend.database import SessionLocal
from backend.hsk_models import HSKGrammarPoint

SOURCE = Path(
    "/tmp/hsk-3.0-source/New HSK (2025)/HSK Grammar/json/HSK 7-9.json"
)

LEVEL = "HSK 7–9"
VERSION = "2025"
REPOSITORY = "krmanik/HSK-3.0"
SOURCE_FILE = "HSK 7-9.json"
SOURCE_URL = (
    "https://github.com/krmanik/HSK-3.0/blob/main/"
    "New%20HSK%20(2025)/HSK%20Grammar/json/HSK%207-9.json"
)


def load_records():
    if not SOURCE.is_file():
        raise FileNotFoundError(f"找不到源文件：{SOURCE}")

    records = json.loads(SOURCE.read_text(encoding="utf-8"))

    if not isinstance(records, list):
        raise ValueError("源文件顶层必须是 JSON 数组。")

    required = ("类别", "类别名称", "细目", "语法内容")
    seen_indices = set()
    prepared = []

    for index, item in enumerate(records):
        if not isinstance(item, dict):
            raise ValueError(f"第 {index} 条不是 JSON 对象。")

        for field in required:
            if field not in item or item[field] is None:
                raise ValueError(f"第 {index} 条缺少字段：{field}")

        content = str(item["语法内容"]).strip()
        if not content:
            raise ValueError(f"第 {index} 条语法内容为空。")

        if index in seen_indices:
            raise ValueError(f"发现重复 source_index：{index}")
        seen_indices.add(index)

        prepared.append({
            "level": LEVEL,
            "category": str(item["类别"]),
            "category_name": str(item["类别名称"]),
            "subcategory": str(item["细目"]),
            "content": content,
            "syllabus_version": VERSION,
            "source_repo": REPOSITORY,
            "source_file": SOURCE_FILE,
            "source_url": SOURCE_URL,
            "source_index": index,
        })

    return prepared


def main():
    parser = argparse.ArgumentParser(
        description="HSK 2025 HSK 7–9 grammar safe importer"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="确认预览结果后，实际写入新增记录",
    )
    args = parser.parse_args()

    records = load_records()
    session = SessionLocal()

    try:
        existing = session.query(HSKGrammarPoint).filter_by(
            syllabus_version=VERSION,
            level=LEVEL,
            source_file=SOURCE_FILE,
        ).all()

        existing_by_index = {
            row.source_index: row for row in existing
        }

        new_records = []
        identical = []
        conflicts = []

        for item in records:
            old = existing_by_index.get(item["source_index"])

            if old is None:
                new_records.append(item)
                continue

            same = all(
                getattr(old, field) == value
                for field, value in item.items()
            )

            if same:
                identical.append(item["source_index"])
            else:
                conflicts.append({
                    "source_index": item["source_index"],
                    "database_content": old.content,
                    "source_content": item["content"],
                })

        print("===== HSK 7–9 语法导入预览 =====")
        print("源文件记录：", len(records))
        print("预计新增：", len(new_records))
        print("完全相同、跳过：", len(identical))
        print("内容或来源冲突：", len(conflicts))

        if conflicts:
            print("\n冲突详情（最多显示10条）：")
            for conflict in conflicts[:10]:
                print(conflict)

            print("\n发现冲突，停止导入。请先人工核对。")
            return

        if not args.apply:
            print("\n当前为预览模式，没有写入数据库。")
            print("确认结果后，才使用 --apply 执行导入。")
            return

        for item in new_records:
            session.add(HSKGrammarPoint(**item))

        session.commit()

        saved_count = session.query(HSKGrammarPoint).filter_by(
            syllabus_version=VERSION,
            level=LEVEL,
            source_file=SOURCE_FILE,
        ).count()

        expected_count = len(existing) + len(new_records)

        print("\n===== 导入结果 =====")
        print("本次新增：", len(new_records))
        print("导入后该文件记录总数：", saved_count)
        print("预期记录总数：", expected_count)
        print("数量核对：", "通过" if saved_count == expected_count else "不一致")

        if saved_count != expected_count:
            print("警告：数量不一致，请检查数据库。")

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
