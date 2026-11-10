from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.database import Base, get_db
import backend.models
import backend.auth_models
import backend.hsk_models
from backend.grammar import models as grammar
from backend.master_curriculum import models as master
from backend.master_curriculum.routes import router
from backend.auth_models import User
from backend import auth_routes

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
event.listen(
    engine, "connect",
    lambda conn, rec: conn.execute("PRAGMA foreign_keys=ON"),
)
TestingSession = sessionmaker(bind=engine, autoflush=False)
Base.metadata.create_all(engine)

active_teacher = {"username": "teacher1"}


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


def override_teacher():
    with TestingSession() as db:
        return db.query(User).filter(
            User.username == active_teacher["username"]
        ).one()


app = FastAPI()
app.include_router(router)
app.dependency_overrides[get_db] = override_db
app.dependency_overrides[auth_routes.get_current_teacher] = override_teacher
client = TestClient(app)


def check(response, expected, label):
    assert response.status_code == expected, (
        f"{label}: expected {expected}, got "
        f"{response.status_code}: {response.text}"
    )
    print(f"PASS: {label}")


with TestingSession.begin() as db:
    t1 = User(username="teacher1", hashed_password="test")
    t2 = User(username="teacher2", hashed_password="test")
    db.add_all([t1, t2])
    db.flush()

    hsk = backend.hsk_models.HSKVocabulary(
        number=990001, level="HSK1",
        simplified="吃", traditional="吃", pinyin="chī",
        english="to eat", source_repo="test", source_file="test",
    )
    g1 = grammar.GrammarKnowledgePoint(
        teacher_user_id=t1.id, title="动词谓语句",
    )
    g2 = grammar.GrammarKnowledgePoint(
        teacher_user_id=t2.id, title="比较句",
    )
    db.add_all([hsk, g1, g2])
    db.flush()
    hsk_id, grammar1_id = hsk.id, g1.id

with client:
    # 教师1：基础数据创建和读取
    vocabulary = client.post("/api/master/vocabularies", json={
        "simplified": "吃", "pinyin": "chī",
        "translations": {"fr": "manger"},
    })
    check(vocabulary, 201, "创建核心词汇")
    vocab_id = vocabulary.json()["id"]

    check(client.get("/api/master/vocabularies"), 200, "读取核心词汇")
    check(client.post("/api/master/levels", json={
        "level_code": "MASTER-1", "title": "Master一级",
    }), 201, "创建课程等级")
    level_id = client.get("/api/master/levels").json()["items"][0]["id"]

    unit = client.post("/api/master/units", json={
        "level_id": level_id, "unit_code": "M1-U1",
        "title": "核心生存动词",
    })
    check(unit, 201, "创建课程单元")
    unit_id = unit.json()["id"]
    check(client.get("/api/master/units"), 200, "读取课程单元")

    scenario = client.post("/api/master/scenarios", json={
        "name": "餐厅点单", "domain": "日常生活",
    })
    check(scenario, 201, "创建教学场景")
    scenario_id = scenario.json()["id"]
    check(client.get("/api/master/scenarios"), 200, "读取教学场景")

    # 四种关联接口
    check(client.post(
        f"/api/master/vocabularies/{vocab_id}/hsk-links",
        json={"hsk_vocabulary_id": hsk_id},
    ), 201, "核心词汇关联共享HSK词条")

    check(client.post(
        f"/api/master/vocabularies/{vocab_id}/grammar-links",
        json={"grammar_point_id": grammar1_id},
    ), 201, "核心词汇关联语法")

    check(client.post(
        f"/api/master/units/{unit_id}/vocabulary-links",
        json={"core_vocabulary_id": vocab_id},
    ), 201, "单元关联核心词汇")

    check(client.post(
        f"/api/master/units/{unit_id}/grammar-links",
        json={"grammar_point_id": grammar1_id},
    ), 201, "单元关联语法")

    check(client.post(
        f"/api/master/units/{unit_id}/scenario-links",
        json={"scenario_id": scenario_id},
    ), 201, "单元关联教学场景")

    # 重复关联必须返回409
    check(client.post(
        f"/api/master/units/{unit_id}/scenario-links",
        json={"scenario_id": scenario_id},
    ), 409, "重复场景关联返回409")

    # 无效ID和无效输入
    check(client.post("/api/master/units/999999/scenario-links",
        json={"scenario_id": scenario_id}),
        404, "不存在的单元返回404")

    check(client.post("/api/master/vocabularies", json={
        "simplified": "", "pinyin": "chi",
    }), 422, "无效词汇输入返回422")

    # 教师2：数据隔离和跨教师关联拦截
    active_teacher["username"] = "teacher2"

    vocab_list = client.get("/api/master/vocabularies")
    check(vocab_list, 200, "教师2读取自己的词汇列表")
    assert vocab_list.json()["total"] == 0
    print("PASS: 教师2看不到教师1的核心词汇")

    level2 = client.post("/api/master/levels", json={
        "level_code": "MASTER-1", "title": "教师2一级",
    })
    check(level2, 201, "教师2创建自己的等级")
    unit2 = client.post("/api/master/units", json={
        "level_id": level2.json()["id"],
        "unit_code": "M1-U1", "title": "教师2单元",
    })
    check(unit2, 201, "教师2创建自己的单元")
    unit2_id = unit2.json()["id"]

    scenario2 = client.post("/api/master/scenarios", json={
        "name": "购物", "domain": "日常生活",
    })
    check(scenario2, 201, "教师2创建自己的场景")

    vocab2 = client.post("/api/master/vocabularies", json={
        "simplified": "买", "pinyin": "mǎi",
    })
    check(vocab2, 201, "教师2创建自己的词汇")
    vocab2_id = vocab2.json()["id"]

    check(client.post(
        f"/api/master/vocabularies/{vocab2_id}/grammar-links",
        json={"grammar_point_id": grammar1_id},
    ), 404, "阻止跨教师词汇—语法关联")

    check(client.post(
        f"/api/master/units/{unit2_id}/grammar-links",
        json={"grammar_point_id": grammar1_id},
    ), 404, "阻止跨教师单元—语法关联")

    check(client.post(
        f"/api/master/units/{unit2_id}/scenario-links",
        json={"scenario_id": scenario_id},
    ), 404, "阻止跨教师单元—场景关联")

    check(client.post(
        f"/api/master/units/{unit2_id}/vocabulary-links",
        json={"core_vocabulary_id": vocab_id},
    ), 404, "阻止跨教师单元—词汇关联")

print("\n全部 Master API 测试通过。")
print("测试数据库：内存 SQLite")
print("正式数据库：未连接、未修改")
engine.dispose()
