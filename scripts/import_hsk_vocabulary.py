import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import func
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.database import SessionLocal, engine
from backend.hsk_models import HSKVocabulary


DATA_FILE = (
    ROOT / "data" / "hsk" / "2025" / "vocabulary"
    / "hsk-3-0-all-levels.json"
)

REPOSITORY = "milayan250101-coder/hsk-platform"
SOURCE_FILE = DATA_FILE.name

LEVEL_RANGES = [
    (1, 300, "HSK 1"),
    (301, 500, "HSK 2"),
    (501, 1000, "HSK 3"),
    (1001, 2000, "HSK 4"),
    (2001, 3600, "HSK 5"),
    (3601, 5400, "HSK 6"),
    (5401, 11000, "HSK 7–9"),
]

REQUIRED_FIELDS = {
    "number", "simplified", "traditional",
    "pinyin", "english", "partOfSpeech",
}


def get_level(number):
    for start, end, level in LEVEL_RANGES:
        if start <= number <= end:
            return level
    raise ValueError(f"无法确定编号 {number} 的 HSK 级别")


def load_and_validate():
    if not DATA_FILE.is_file():
        raise FileNotFoundError(f"找不到文件：{DATA_FILE}")

    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError("JSON 根节点必须是对象")

    terms = data.get("terms")
    if not isinstance(terms, list):
        raise ValueError("terms 必须是数组")

    if data.get("totalTerms") != 11000 or len(terms) != 11000:
        raise ValueError(
            f"词条总数不符：totalTerms={data.get('totalTerms')}，"
            f"实际={len(terms)}"
        )

    numbers = set()
    rows = []

    for index, item in enumerate(terms, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"第 {index} 条不是对象")

        missing = REQUIRED_FIELDS - item.keys()
        if missing:
            raise ValueError(f"第 {index} 条缺少字段：{sorted(missing)}")

        number = item["number"]
        if not isinstance(number, int) or isinstance(number, bool):
            raise ValueError(f"第 {index} 条 number 不是整数")

        if number in numbers:
            raise ValueError(f"发现重复编号：{number}")
        numbers.add(number)

        for field in REQUIRED_FIELDS - {"number"}:
            if not isinstance(item[field], str):
                raise ValueError(f"第 {index} 条字段 {field} 不是字符串")

        rows.append({
            "number": number,
            "level": get_level(number),
            "simplified": item["simplified"],
            "traditional": item["traditional"],
            "pinyin": item["pinyin"],
            "english": item["english"],
            "part_of_speech": item["partOfSpeech"],
            "syllabus_version": "2025",
            "source_repo": REPOSITORY,
            "source_file": SOURCE_FILE,
            "dictionary_source": "CC-CEDICT",
            "dictionary_license": "CC BY-SA 4.0",
            "imported_at": datetime.utcnow(),
        })

    if numbers != set(range(1, 11001)):
        raise ValueError("编号不是完整的 1–11000")

    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="正式写入数据库；不加此参数时只检查",
    )
    args = parser.parse_args()

    rows = load_and_validate()

    print("JSON 检查通过")
    print("词条总数：", len(rows))

    for _, _, level in LEVEL_RANGES:
        count = sum(row["level"] == level for row in rows)
        print(f"{level}：{count}")

    if not args.apply:
        print("\n预检查完成：没有写入数据库。")
        print("确认无误后，使用 --apply 执行正式导入。")
        return

    session = SessionLocal()
    inserted = 0
    updated = 0

    try:
        existing = {
            number for (number,) in session.query(
                HSKVocabulary.number
            ).all()
        }

        inserted = sum(row["number"] not in existing for row in rows)
        updated = len(rows) - inserted

        table = HSKVocabulary.__table__

        for start in range(0, len(rows), 500):
            batch = rows[start:start + 500]
            statement = sqlite_insert(table).values(batch)
            statement = statement.on_conflict_do_update(
                index_elements=["number"],
                set_={
                    key: getattr(statement.excluded, key)
                    for key in batch[0]
                    if key not in {"id", "number"}
                },
            )
            session.execute(statement)

        session.commit()

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    print("\n=== HSK 词汇导入完成 ===")
    print("新增：", inserted)
    print("更新：", updated)


if __name__ == "__main__":
    main()
