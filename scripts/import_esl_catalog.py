import argparse
import json
from pathlib import Path

from sqlalchemy import select

from backend.database import SessionLocal
from backend.esl_catalog_models import ESLTopicCatalog


JSON_FILE = Path("esl_catalog_preview.json")


def load_records():
    if not JSON_FILE.exists():
        raise FileNotFoundError(f"找不到文件：{JSON_FILE}")

    with JSON_FILE.open("r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError("JSON 顶层必须是列表")

    required_fields = {
        "title_en",
        "letter",
        "category",
        "source_url",
        "title_zh",
        "pinyin",
    }

    for index, item in enumerate(records, start=1):
        missing = required_fields - set(item.keys())
        if missing:
            raise ValueError(f"第 {index} 条缺少字段：{sorted(missing)}")

        if not item["title_en"] or not item["source_url"]:
            raise ValueError(f"第 {index} 条英文标题或 URL 为空")

    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只检查数据，不写入数据库",
    )
    args = parser.parse_args()

    records = load_records()

    print("JSON 记录数：", len(records))

    category_counts = {}
    for item in records:
        category = item["category"]
        category_counts[category] = category_counts.get(category, 0) + 1

    print("分类统计：", category_counts)

    if args.dry_run:
        print("预览模式：没有写入数据库。")
        return

    db = SessionLocal()
    inserted = 0
    updated = 0
    unchanged = 0

    try:
        for item in records:
            existing = db.execute(
                select(ESLTopicCatalog).where(
                    ESLTopicCatalog.source_url == item["source_url"]
                )
            ).scalar_one_or_none()

            if existing is None:
                db.add(
                    ESLTopicCatalog(
                        title_en=item["title_en"],
                        letter=item["letter"],
                        category=item["category"],
                        source_url=item["source_url"],
                        title_zh=item["title_zh"],
                        pinyin=item["pinyin"],
                        translation_status="pending",
                    )
                )
                inserted += 1
            else:
                changed = False
                for field in (
                    "title_en",
                    "letter",
                    "category",
                    "title_zh",
                    "pinyin",
                ):
                    new_value = item[field]
                    if getattr(existing, field) != new_value:
                        setattr(existing, field, new_value)
                        changed = True

                if existing.translation_status != "translated":
                    existing.translation_status = "pending"

                if changed:
                    updated += 1
                else:
                    unchanged += 1

        db.commit()

        print("导入完成")
        print("新增：", inserted)
        print("更新：", updated)
        print("未变化：", unchanged)

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
