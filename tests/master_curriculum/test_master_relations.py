from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from backend.database import Base
import backend.auth_models
import backend.models
import backend.hsk_models
from backend.grammar import models as grammar
from backend.master_curriculum import models as master

engine = create_engine("sqlite:///:memory:")
event.listen(engine, "connect", lambda conn, rec: conn.execute("PRAGMA foreign_keys=ON"))
Base.metadata.create_all(engine)
tables = Base.metadata.tables

def add(conn, table, **values):
    result = conn.execute(tables[table].insert().values(**values))
    return result.inserted_primary_key[0]

with engine.begin() as db:
    teacher1 = add(db, "users", username="teacher1", hashed_password="test")
    teacher2 = add(db, "users", username="teacher2", hashed_password="test")

    hsk4 = add(db, "hsk_vocabulary", number=1, level="HSK4",
               simplified="乘", traditional="乘", pinyin="chéng",
               english="to ride", source_repo="test", source_file="test")
    hsk6 = add(db, "hsk_vocabulary", number=2, level="HSK6",
               simplified="乘", traditional="乘", pinyin="chéng",
               english="to ride", source_repo="test", source_file="test")

    grammar_id = add(db, "grammar_knowledge_points",
                     teacher_user_id=teacher1, title="结果补语")

    word1 = add(db, "core_vocabularies",
                teacher_user_id=teacher1, simplified="乘", pinyin="chéng")
    word2 = add(db, "core_vocabularies",
                teacher_user_id=teacher2, simplified="乘", pinyin="chéng")
    print("PASS 1：不同教师可以分别建立相同核心词汇")

    add(db, "core_vocabulary_hsk_links",
        core_vocabulary_id=word1, hsk_vocabulary_id=hsk4)
    add(db, "core_vocabulary_hsk_links",
        core_vocabulary_id=word1, hsk_vocabulary_id=hsk6)
    print("PASS 2：一个核心词汇可以关联多个HSK等级词条")

    level = add(db, "master_course_levels",
                teacher_user_id=teacher1, level_code="MASTER-1", title="Master一级")
    unit = add(db, "master_course_units",
               teacher_user_id=teacher1, level_id=level,
               unit_code="M1-U1", title="核心动词")
    scenario = add(db, "teaching_scenarios",
                   teacher_user_id=teacher1, name="日常出行")
    add(db, "master_unit_vocabularies",
        unit_id=unit, core_vocabulary_id=word1)
    add(db, "master_unit_grammar_points",
        unit_id=unit, grammar_point_id=grammar_id)
    add(db, "master_unit_scenarios",
        unit_id=unit, scenario_id=scenario)
    print("PASS 3：课程单元成功关联词汇、语法和场景")

    try:
        with db.begin_nested():
            db.execute(tables["core_vocabulary_hsk_links"].insert().values(
                core_vocabulary_id=word1, hsk_vocabulary_id=hsk4))
    except IntegrityError:
        print("PASS 4：重复HSK关联被唯一约束拦截")
    else:
        raise AssertionError("重复HSK关联没有被拦截")

    try:
        with db.begin_nested():
            db.execute(tables["core_vocabularies"].insert().values(
                teacher_user_id=teacher1, simplified="乘", pinyin="chéng"))
    except IntegrityError:
        print("PASS 5：同一教师重复核心词汇被唯一约束拦截")
    else:
        raise AssertionError("重复核心词汇没有被拦截")

print("\n全部关联测试通过。")
print("测试数据库：内存 SQLite")
print("正式数据库：未连接、未修改")
engine.dispose()
