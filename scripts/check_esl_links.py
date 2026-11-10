from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from backend.database import SessionLocal
from backend.esl_catalog_models import ESLTopicCatalog

db = SessionLocal()
try:
    rows = db.query(ESLTopicCatalog).order_by(ESLTopicCatalog.id).all()
    items = [(r.id, r.title_en, r.source_url or "") for r in rows]
finally:
    db.close()

def check(x):
    try:
        req = Request(x[2], headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=12) as r:
            return x, r.status
    except HTTPError as e:
        return x, e.code
    except Exception as e:
        return x, str(e)

results = []
with ThreadPoolExecutor(max_workers=5) as pool:
    futures = [pool.submit(check, x) for x in items]
    for f in as_completed(futures):
        results.append(f.result())

bad = [(x, s) for x, s in results if not isinstance(s, int) or s >= 400]
print("总数：", len(results), "可访问：", len(results)-len(bad), "需复核：", len(bad))
for x, s in sorted(bad, key=lambda v: v[0][0]):
    print(f"ID {x[0]} | {x[1]} | {s} | {x[2]}")
