import re
import json
from urllib.parse import urljoin, urlparse
from collections import Counter
import requests
from bs4 import BeautifulSoup

from backend.database import SessionLocal
from backend.esl_catalog_models import ESLTopicCatalog

BASE = "https://esldiscussions.com/"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def norm(text):
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())

def clean_url(url):
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}{p.path}".rstrip("/").lower()

response = requests.get(BASE, headers=HEADERS, timeout=30)
response.raise_for_status()
soup = BeautifulSoup(response.text, "html.parser")

official = {}
for a in soup.find_all("a", href=True):
    href = urljoin(BASE, a["href"])
    parsed = urlparse(href)
    path = parsed.path.lower()

    if parsed.netloc.lower() not in ("esldiscussions.com", "www.esldiscussions.com"):
        continue
    if not re.fullmatch(r"/[a-z]/[^/]+\.html", path):
        continue

    title = a.get_text(" ", strip=True)
    if not title:
        continue

    category = "alphabetical"
    if path.startswith("/g/"):
        category = "grammar"
    elif path.startswith("/i/"):
        category = "idioms"

    key = (category, norm(title))
    official.setdefault(key, {
        "title": title,
        "category": category,
        "url": clean_url(href),
    })

db = SessionLocal()
try:
    rows = db.query(ESLTopicCatalog).all()
    database = {}
    for row in rows:
        category = (getattr(row, "category", None) or "alphabetical").lower()
        if category not in ("grammar", "idioms"):
            category = "alphabetical"
        key = (category, norm(row.title_en))
        database.setdefault(key, []).append({
            "id": row.id,
            "title": row.title_en,
            "url": clean_url(row.source_url or ""),
            "category": category,
        })
finally:
    db.close()

missing = [v for k, v in official.items() if k not in database]
extra = [
    item
    for k, items in database.items()
    if k not in official
    for item in items
]
duplicates = [
    {"title": k[1], "records": v}
    for k, v in database.items()
    if len(v) > 1
]
url_mismatch = []
for key, items in database.items():
    if key in official:
        for item in items:
            if item["url"] and item["url"] != official[key]["url"]:
                url_mismatch.append({
                    "title": item["title"],
                    "db_url": item["url"],
                    "official_url": official[key]["url"],
                })

report = {
    "official_unique_topics": len(official),
    "official_by_category": dict(Counter(v["category"] for v in official.values())),
    "database_records": len(rows),
    "missing_from_database": missing,
    "database_not_in_official_directory": extra,
    "duplicate_database_titles": duplicates,
    "url_mismatches": url_mismatch,
}

with open("esl_catalog_audit_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print("官网目录抓取成功")
print("官网目录去重主题数：", report["official_unique_topics"])
print("官网分类数量：", report["official_by_category"])
print("数据库记录数：", report["database_records"])
print("官网有、数据库缺少：", len(missing))
print("数据库有、官网目录未列出：", len(extra))
print("数据库重复标题：", len(duplicates))
print("链接不一致：", len(url_mismatch))
print("差异报告：esl_catalog_audit_report.json")
if missing:
    print("\n===== 官网遗漏主题（前40条）=====")
    for item in missing[:40]:
        print(f'{item["category"]} | {item["title"]} | {item["url"]}')
