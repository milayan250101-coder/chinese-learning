import json
import re
from pathlib import Path
from difflib import SequenceMatcher

BASE = Path("migration-import")

def load_json(name):
    return json.loads((BASE / name).read_text(encoding="utf-8"))

def normalize(text):
    return re.sub(r"\s+", "", str(text or "")).lower()

def bigrams(text):
    text = normalize(text)
    if len(text) < 2:
        return {text} if text else set()
    return {text[i:i + 2] for i in range(len(text) - 1)}

def similarity(a, b):
    a, b = normalize(a), normalize(b)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 1.0
    aa, bb = bigrams(a), bigrams(b)
    overlap = len(aa & bb) / len(aa | bb) if aa | bb else 0
    sequence = SequenceMatcher(None, a, b).ratio()
    return max(overlap, sequence * 0.85)

index = load_json("grammar-search-index.json")
grammar = load_json("hsk-grammar-reference.json")

results = []

for entry in index:
    keyword = entry["keyword"]
    searchable = [
        keyword,
        entry["slug"].replace("-", " "),
    ]

    scored = []
    for point in grammar:
        content = " ".join([
            str(point.get("category", "")),
            str(point.get("category_name", "")),
            str(point.get("subcategory", "")),
            str(point.get("content", "")),
        ])
        score = max(similarity(term, content) for term in searchable)
        scored.append({
            "grammar_point_id": point["id"],
            "hsk_level": point["level"],
            "category": point.get("category", ""),
            "category_name": point.get("category_name", ""),
            "subcategory": point.get("subcategory", ""),
            "content": point.get("content", ""),
            "text_similarity": round(score, 4),
        })

    scored.sort(key=lambda x: (-x["text_similarity"], x["grammar_point_id"]))

    results.append({
        "keyword": keyword,
        "slug": entry["slug"],
        "mapping_status": "ai_review_required",
        "grammar_point_ids": [],
        "candidates": scored[:10],
    })

output = BASE / "grammar-mapping-candidates.json"
output.write_text(
    json.dumps(results, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("语法目录：", len(index))
print("正式语法点：", len(grammar))
print("生成候选目录：", len(results))
print("每条最多候选：10")
print("输出文件：", output)
print("注意：相似度仅用于初筛，尚未确认任何映射。")
