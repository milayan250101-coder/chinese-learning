from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from collections import Counter
import requests
import json
import re

SOURCE_URL = "https://esldiscussions.com/"
HEADERS = {"User-Agent": "Mozilla/5.0"}

class TopicParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.href = None
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.parts = []

    def handle_data(self, data):
        if self.href:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.href:
            title = " ".join("".join(self.parts).split())
            self.links.append((self.href, title))
            self.href = None
            self.parts = []


def classify(path):
    if re.fullmatch(r"/[a-z]/[^/]+\.html", path):
        return "alphabetical", path[1].upper()

    if re.fullmatch(r"/grammar/[^/]+\.html", path):
        return "grammar", "Grammar"

    if re.fullmatch(r"/idioms/[^/]+\.html", path):
        return "idioms", "Idioms"

    return None, None


def main():
    print("正在读取 ESL Discussions 首页……")

    response = requests.get(
        SOURCE_URL,
        headers=HEADERS,
        timeout=30
    )
    response.raise_for_status()

    parser = TopicParser()
    parser.feed(response.text)

    topics = []
    seen_urls = set()

    for href, title in parser.links:
        if not href or not title:
            continue

        url = urljoin(SOURCE_URL, href)
        parsed = urlparse(url)

        if parsed.netloc.lower() not in {
            "esldiscussions.com",
            "www.esldiscussions.com"
        }:
            continue

        category, group = classify(parsed.path.lower())

        if not category:
            continue

        if url in seen_urls:
            continue

        seen_urls.add(url)

        topics.append({
            "title_en": title,
            "letter": group if category == "alphabetical" else None,
            "category": category,
            "source_url": url,
            "title_zh": None,
            "pinyin": None
        })

    topics.sort(key=lambda item: (
        item["category"],
        item["letter"] or "",
        item["title_en"].casefold()
    ))

    counts = Counter(item["category"] for item in topics)

    print("\n===== 完整目录预览 =====")
    print("首页链接数量：", len(parser.links))
    print("识别的话题总数：", len(topics))
    print("分类数量：", dict(counts))

    print("\n===== A-Z 各字母数量 =====")
    letter_counts = Counter(
        item["letter"]
        for item in topics
        if item["category"] == "alphabetical"
    )

    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        print(f"{letter}: {letter_counts.get(letter, 0)}")

    print("\n===== Grammar 样本 =====")
    for item in [x for x in topics if x["category"] == "grammar"][:10]:
        print(item["title_en"], "|", item["source_url"])

    print("\n===== Idioms 样本 =====")
    for item in [x for x in topics if x["category"] == "idioms"][:10]:
        print(item["title_en"], "|", item["source_url"])

    with open(
        "esl_catalog_preview.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(topics, file, ensure_ascii=False, indent=2)

    print("\n预览文件已保存：esl_catalog_preview.json")
    print("本脚本不会写入数据库。")


if __name__ == "__main__":
    main()
