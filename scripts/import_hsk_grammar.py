import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.database import Base, SessionLocal, engine
from backend.hsk_models import HSKGrammarPoint


REPOSITORY = "krmanik/HSK-3.0"
VERSION = "2025"

DATA_DIR = ROOT / "data" / "hsk" / VERSION / "grammar"
DATA_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = (
    "https://raw.githubusercontent.com/krmanik/HSK-3.0/main/"
    "New%20HSK%20(2025)/HSK%20Grammar/json/"
)

LEVELS = range(1, 7)

REQUIRED_FIELDS = {
    "类别",
    "类别名称",
    "细目",
    "语法内容",
}


def download_json(level: int):
    filename = f"HSK {level}.json"
    url = BASE_URL + f"HSK%20{level}.json"

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ChineseLearning-HSK-Importer"},
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()

    data = json.loads(raw.decode("utf-8"))

    if not isinstance(data, list):
        raise ValueError(f"{filename} 不是 JSON 数组")

    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(
                f"{filename} 第 {index + 1} 条不是对象"
            )

        missing = REQUIRED_FIELDS - item.keys()
        if missing:
            raise ValueError(
                f"{filename} 第 {index + 1} 条缺少字段：{missing}"
            )

        if not all(
            isinstance(item[field], str)
            for field in REQUIRED_FIELDS
        ):
            raise ValueError(
                f"{filename} 第 {index + 1} 条存在非字符串字段"
            )

    # 保存未经转换的原始 JSON
    raw_path = DATA_DIR / filename
    raw_path.write_bytes(raw)

    return data, filename, url


def import_all():
    Base.metadata.create_all(bind=engine)

    # 先下载并验证全部六级，再开始数据库事务
    downloaded = []

    for level in LEVELS:
        data, filename, url = download_json(level)
        downloaded.append((level, data, filename, url))
        print(f"已下载并验证 HSK {level}：{len(data)} 条")

    db = SessionLocal()

    inserted = 0
    updated = 0

    try:
        for level, data, filename, url in downloaded:
            level_name = f"HSK {level}"

            for index, item in enumerate(data):
                record = (
                    db.query(HSKGrammarPoint)
                    .filter_by(
                        syllabus_version=VERSION,
                        level=level_name,
                        source_file=filename,
                        source_index=index,
                    )
                    .first()
                )

                values = {
                    "category": item["类别"],
                    "category_name": item["类别名称"],
                    "subcategory": item["细目"],
                    "content": item["语法内容"],
                    "source_repo": REPOSITORY,
                    "source_file": filename,
                    "source_url": url,
                    "imported_at": datetime.utcnow(),
                }

                if record is None:
                    record = HSKGrammarPoint(
                        syllabus_version=VERSION,
                        level=level_name,
                        source_index=index,
                        **values,
                    )
                    db.add(record)
                    inserted += 1
                else:
                    for key, value in values.items():
                        setattr(record, key, value)
                    updated += 1

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

    print("\n=== HSK 语法导入完成 ===")
    print("新增：", inserted)
    print("更新：", updated)
    print("原始文件目录：", DATA_DIR)


if __name__ == "__main__":
    import_all()
