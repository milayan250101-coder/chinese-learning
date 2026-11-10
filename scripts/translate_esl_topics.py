import os
import json
import argparse
import requests

from backend.database import SessionLocal
from backend.esl_catalog_models import ESLTopicCatalog

API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-flash"
OUTPUT_FILE = "esl_translation_preview.json"


def translate_topics(rows):
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("未找到 DEEPSEEK_API_KEY 环境变量。")

    topics = [
        {
            "id": row.id,
            "title_en": row.title_en,
            "category": row.category
        }
        for row in rows
    ]

    system_prompt = """
你是一位专业的中文教育编辑，负责翻译英语讨论话题目录。

请根据英文标题及其分类，给出自然、准确、适合中文学习网站使用的中文话题名称。

要求：
1. 保留原英文标题的实际含义。
2. 中文译名应简洁、自然，不要机械直译。
3. 人名、国家名、电影奖项、专有名词应使用通行中文名称。
4. Grammar 分类应使用准确的中文语法术语。
5. Idioms 分类应根据英文标题的含义翻译。
6. 不要添加原英文标题没有表达的信息。
7. 拼音使用标准汉语拼音，包含正确声调符号。
8. 不要翻译英文原文中的讨论题，因为这里只处理话题标题。

必须输出有效 JSON，格式如下：
{
  "translations": [
    {
      "id": 1,
      "title_zh": "中文话题名称",
      "pinyin": "zhōng wén huà tí míng chēng"
    }
  ]
}
"""

    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        topics,
                        ensure_ascii=False
                    ) + "\n请翻译以上全部话题，并以 JSON 格式返回。"
                }
            ],
            "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
            "temperature": 0.2,
            "max_tokens": 4000,
            "stream": False
        },
        timeout=120
    )

    if not response.ok:
        raise RuntimeError(
            f"DeepSeek 请求失败：HTTP {response.status_code}"
        )

    content = response.json()["choices"][0]["message"]["content"]
    result = json.loads(content)

    translations = result.get("translations")
    if not isinstance(translations, list):
        raise ValueError("AI 返回结果缺少 translations 数组。")

    expected_ids = {row.id for row in rows}
    received_ids = set()

    for item in translations:
        if not isinstance(item, dict):
            raise ValueError("翻译记录格式不正确。")

        topic_id = item.get("id")
        title_zh = item.get("title_zh")
        pinyin = item.get("pinyin")

        if topic_id not in expected_ids:
            raise ValueError(f"出现未知话题 ID：{topic_id}")

        if topic_id in received_ids:
            raise ValueError(f"出现重复话题 ID：{topic_id}")

        if not isinstance(title_zh, str) or not title_zh.strip():
            raise ValueError(f"话题 {topic_id} 缺少中文译名。")

        if not isinstance(pinyin, str) or not pinyin.strip():
            raise ValueError(f"话题 {topic_id} 缺少拼音。")

        received_ids.add(topic_id)

    if received_ids != expected_ids:
        raise ValueError("AI 返回的话题数量不完整，不能保存。")

    return translations



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--save",
        action="store_true",
        help="读取已审核的 JSON 预览文件并写入数据库"
    )
    args = parser.parse_args()

    if args.limit < 1 or args.limit > 100:
        raise ValueError("每批数量必须在 1 到 100 之间。")

    db = SessionLocal()

    try:
        rows = (
            db.query(ESLTopicCatalog)
            .filter(ESLTopicCatalog.title_zh.is_(None))
            .order_by(ESLTopicCatalog.id)
            .limit(args.limit)
            .all()
        )

        if not rows:
            print("没有待翻译的话题。")
            return

        expected_ids = {row.id for row in rows}
        print(f"当前待处理话题：{len(rows)} 条")

        if args.save:
            print("正在读取已审核的 JSON 文件……")

            with open(OUTPUT_FILE, "r", encoding="utf-8") as file:
                translations = json.load(file)

            if not isinstance(translations, list):
                raise ValueError("预览文件必须是 JSON 数组。")

            translation_map = {}

            for item in translations:
                if not isinstance(item, dict):
                    raise ValueError("预览记录格式不正确。")

                topic_id = item.get("id")
                title_zh = item.get("title_zh")
                pinyin = item.get("pinyin")

                if topic_id in translation_map:
                    raise ValueError(f"重复的话题 ID：{topic_id}")

                if not isinstance(title_zh, str) or not title_zh.strip():
                    raise ValueError(f"话题 {topic_id} 缺少中文译名。")

                if not isinstance(pinyin, str) or not pinyin.strip():
                    raise ValueError(f"话题 {topic_id} 缺少拼音。")

                translation_map[topic_id] = item

            if set(translation_map) != expected_ids:
                raise ValueError(
                    "预览文件中的 ID 与当前待处理话题不完全匹配，"
                    "已取消保存。"
                )

            print("\n即将写入以下审核内容：")
            for row in rows:
                item = translation_map[row.id]
                print(
                    f"{row.id} | {row.title_en} | "
                    f"{item['title_zh']} | {item['pinyin']}"
                )

            saved = 0
            for row in rows:
                item = translation_map[row.id]

                if row.title_zh is not None or row.pinyin is not None:
                    raise ValueError(
                        f"话题 {row.id} 已有中文内容，为避免覆盖，取消保存。"
                    )

                row.title_zh = item["title_zh"].strip()
                row.pinyin = item["pinyin"].strip()
                row.translation_status = "translated"
                saved += 1

            db.commit()
            print(f"\n成功写入数据库：{saved} 条。")
            print("本次保存直接使用审核稿，没有调用 DeepSeek。")

        else:
            print("正在调用 DeepSeek 生成预览……")
            translations = translate_topics(rows)

            with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
                json.dump(
                    translations,
                    file,
                    ensure_ascii=False,
                    indent=2
                )

            print(f"\n预览文件已生成：{OUTPUT_FILE}")

            for item in translations:
                print(
                    f"{item['id']} | "
                    f"{item['title_zh']} | "
                    f"{item['pinyin']}"
                )

            print("\n当前为预览模式，没有写入数据库。")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
