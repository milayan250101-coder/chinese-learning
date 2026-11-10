import argparse
from pathlib import Path
from urllib.parse import quote

from backend.database import SessionLocal
from backend.hsk_hanzi_models import HSKHanzi


SOURCE_DIR = Path("/tmp/hsk-3.0-source/New HSK (2025)/HSK Hanzi")
SOURCE_REPO = "krmanik/HSK-3.0"
VERSION = "2025"

LEVEL_FILES = {
    "HSK_Level_1_hanzi.txt": "1",
    "HSK_Level_2_hanzi.txt": "2",
    "HSK_Level_3_hanzi.txt": "3",
    "HSK_Level_4_hanzi.txt": "4",
    "HSK_Level_5_hanzi.txt": "5",
    "HSK_Level_6_hanzi.txt": "6",
    "HSK_Level_7-9_hanzi.txt": "7-9",
}

EXPECTED_TOTAL = 3088


def load_source():
    records = []

    for filename, level in LEVEL_FILES.items():
        path = SOURCE_DIR / filename

        if not path.is_file():
            raise FileNotFoundError(f"源文件不存在：{path}")

        characters = [
            line.strip()
            for line in path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip()
        ]

        for character in characters:
            if len(character) != 1:
                raise ValueError(
                    f"发现非单个字符条目：{filename}: {character!r}"
                )

            source_path = (
                "New HSK (2025)/HSK Hanzi/" + filename
            )
            source_url = (
                "https://github.com/krmanik/HSK-3.0/blob/main/"
                + quote(source_path, safe="/")
            )

            records.append({
                "character": character,
                "level": level,
                "syllabus_version": VERSION,
                "source_repo": SOURCE_REPO,
                "source_file": filename,
                "source_url": source_url,
            })

    keys = [
        (item["syllabus_version"], item["level"], item["character"])
        for item in records
    ]

    if len(records) != EXPECTED_TOTAL:
        raise ValueError(
            f"源数据数量异常：预期 {EXPECTED_TOTAL}，实际 {len(records)}"
        )

    if len(keys) != len(set(keys)):
        raise ValueError("源文件中存在重复的级别与汉字组合")

    if len({item["character"] for item in records}) != EXPECTED_TOTAL:
        raise ValueError("全级别汉字唯一数量与预期不一致")

    return records


def main():
    parser = argparse.ArgumentParser(
        description="导入 HSK 2025 汉字参考数据"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="确认后正式写入数据库；默认只预览",
    )
    args = parser.parse_args()

    records = load_source()

    print(f"源文件数量：{len(LEVEL_FILES)}")
    print(f"源数据总数：{len(records)}")

    session = SessionLocal()

    try:
        existing_count = 0
        new_records = []

        for item in records:
            existing = session.query(HSKHanzi).filter_by(
                syllabus_version=item["syllabus_version"],
                level=item["level"],
                character=item["character"],
            ).first()

            if existing:
                existing_count += 1
            else:
                new_records.append(item)

        print(f"数据库中已存在：{existing_count}")
        print(f"预计新增：{len(new_records)}")

        if not args.apply:
            print("当前为预览模式，没有写入数据库。")
            print("确认预览结果后，使用 --apply 才会正式导入。")
            return

        for item in new_records:
            session.add(HSKHanzi(**item))

        session.commit()

        final_count = session.query(HSKHanzi).filter_by(
            syllabus_version=VERSION
        ).count()

        print(f"本次新增：{len(new_records)}")
        print(f"数据库中 HSK {VERSION} 汉字总数：{final_count}")

        if final_count != EXPECTED_TOTAL:
            raise RuntimeError(
                f"导入后数量不符：预期 {EXPECTED_TOTAL}，实际 {final_count}"
            )

        print("数量核对通过。")

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
