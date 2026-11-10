import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from backend.database import SessionLocal
from backend.esl_catalog_models import ESLTopicCatalog
from translate_esl_topics import translate_topics

OUTPUT_FILE = Path("esl_translation_remaining_preview.json")
BATCH_SIZE = 100


def get_pending(db):
    return (
        db.query(ESLTopicCatalog)
        .filter(ESLTopicCatalog.title_zh.is_(None))
        .order_by(ESLTopicCatalog.id)
        .all()
    )


def validate_preview(data, expected_ids):
    if not isinstance(data, list):
        raise ValueError("预览文件必须是 JSON 数组。")

    received = set()
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("存在格式错误的记录。")

        topic_id = item.get("id")
        if topic_id not in expected_ids:
            raise ValueError(f"出现未知ID：{topic_id}")
        if topic_id in received:
            raise ValueError(f"出现重复ID：{topic_id}")
        if not isinstance(item.get("title_zh"), str) or not item["title_zh"].strip():
            raise ValueError(f"ID {topic_id} 缺少中文译名。")
        if not isinstance(item.get("pinyin"), str) or not item["pinyin"].strip():
            raise ValueError(f"ID {topic_id} 缺少拼音。")

        received.add(topic_id)

    if received != expected_ids:
        missing = sorted(expected_ids - received)
        raise ValueError(f"预览不完整，缺少ID：{missing}")


def create_backup(db):
    database_path = db.get_bind().url.database
    if not database_path or database_path == ":memory:":
        raise RuntimeError("无法识别 SQLite 数据库文件路径，取消保存。")

    src = Path(database_path)
    if not src.is_absolute():
        src = Path.cwd() / src
    if not src.exists():
        raise FileNotFoundError(f"数据库文件不存在：{src}")

    folder = Path("backups/esl_catalog")
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = folder / f"chinese_learning.db.before_remaining_{stamp}"

    source = sqlite3.connect(src)
    target = sqlite3.connect(dst)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()

    print("数据库备份：", dst)
    print("备份大小：", dst.stat().st_size, "bytes")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        rows = get_pending(db)
        if not rows:
            print("没有待翻译记录。")
            return

        expected_ids = {r.id for r in rows}
        print(f"当前待处理：{len(rows)} 条，ID {rows[0].id}–{rows[-1].id}")

        if not args.save:
            all_translations = []

            for start in range(0, len(rows), BATCH_SIZE):
                chunk = rows[start:start + BATCH_SIZE]
                end = start + len(chunk)
                print(f"\n正在翻译第 {start + 1}–{end} 条，共 {len(rows)} 条……")
                result = translate_topics(chunk)
                all_translations.extend(result)
                print(f"本段完成：{len(result)} 条")

            validate_preview(all_translations, expected_ids)

            all_translations.sort(key=lambda x: x["id"])
            with OUTPUT_FILE.open("w", encoding="utf-8") as f:
                json.dump(all_translations, f, ensure_ascii=False, indent=2)

            print("\n总预览已生成：", OUTPUT_FILE)
            print("预览记录数：", len(all_translations))
            print("ID范围：", all_translations[0]["id"], "–", all_translations[-1]["id"])
            print("数据库未修改。")
            return

        if not OUTPUT_FILE.exists():
            raise FileNotFoundError(f"找不到审核文件：{OUTPUT_FILE}")

        with OUTPUT_FILE.open(encoding="utf-8") as f:
            translations = json.load(f)

        validate_preview(translations, expected_ids)

        for row in rows:
            if row.title_zh is not None or row.pinyin is not None:
                raise ValueError(f"ID {row.id} 已有译名或拼音，取消保存。")

        create_backup(db)

        mapping = {item["id"]: item for item in translations}
        for row in rows:
            item = mapping[row.id]
            row.title_zh = item["title_zh"].strip()
            row.pinyin = item["pinyin"].strip()
            row.translation_status = "translated"

        db.commit()
        print(f"\n成功写入：{len(rows)} 条")
        print("本次保存没有调用 DeepSeek。")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
