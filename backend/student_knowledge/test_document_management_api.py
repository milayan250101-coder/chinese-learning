import unittest
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.auth_routes import get_current_teacher
from backend.student_knowledge.document_management import router
from backend.auth_models import User
from backend.student_profile_models import (
    Student,
    StudentNote,
    StudentNoteFolder,
)

# 注册 StudentNote 所依赖的 lesson_plans 等模型。
from backend import models as _models


class DocumentManagementAPITests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=cls.engine)
        cls.SessionLocal = sessionmaker(
            bind=cls.engine,
            autoflush=False,
            autocommit=False,
        )

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        db = self.SessionLocal()

        teacher_a = User(
            username=f"teacher_api_a_{id(self)}",
            hashed_password="test-only",
        )
        teacher_b = User(
            username=f"teacher_api_b_{id(self)}",
            hashed_password="test-only",
        )
        db.add_all([teacher_a, teacher_b])
        db.flush()

        student_a = Student(
            teacher_user_id=teacher_a.id,
            display_name="测试学生 A",
        )
        student_b = Student(
            teacher_user_id=teacher_b.id,
            display_name="测试学生 B",
        )
        db.add_all([student_a, student_b])
        db.flush()

        folder_b = StudentNoteFolder(
            student_id=student_b.id,
            name="学生 B 的文件夹",
        )
        db.add(folder_b)
        db.commit()

        self.teacher_a_id = teacher_a.id
        self.student_a_id = student_a.id
        self.student_b_id = student_b.id
        self.folder_b_id = folder_b.id

        db.close()

        app = FastAPI()
        app.include_router(router)

        def override_db():
            session = self.SessionLocal()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_teacher] = (
            lambda: SimpleNamespace(id=self.teacher_a_id)
        )

        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def test_folder_create_rename_and_list(self):
        response = self.client.post(
            f"/api/student-knowledge/students/{self.student_a_id}/folders",
            params={
                "name": "等级一",
                "level_name": "初级",
                "sort_order": 1,
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        folder_id = response.json()["id"]

        response = self.client.patch(
            f"/api/student-knowledge/students/{self.student_a_id}"
            f"/folders/{folder_id}",
            params={
                "name": "等级一（已调整）",
                "level_name": "HSK 1",
                "sort_order": 2,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)

        response = self.client.get(
            f"/api/student-knowledge/students/{self.student_a_id}/folders"
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json()["items"][0]["name"],
            "等级一（已调整）",
        )

    def test_pasted_text_document_upload_and_list(self):
        response = self.client.post(
            f"/api/student-knowledge/students/{self.student_a_id}/documents",
            data={
                "title": "测试会议记录",
                "document_type": "meeting_record",
                "source_mode": "pasted_text",
                "chinese_text": "今天我们讨论了中文学习计划。",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)

        created = response.json()
        self.assertEqual(created["document_type"], "meeting_record")
        self.assertEqual(created["source_mode"], "pasted_text")
        self.assertEqual(created["analysis_status"], "not_started")

        response = self.client.get(
            f"/api/student-knowledge/students/{self.student_a_id}/documents"
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["total"], 1)
        self.assertEqual(
            response.json()["items"][0]["content_text"],
            "今天我们讨论了中文学习计划。",
        )

    def test_teacher_cannot_access_another_teachers_student(self):
        paths = [
            (
                "GET",
                f"/api/student-knowledge/students/{self.student_b_id}/folders",
            ),
            (
                "GET",
                f"/api/student-knowledge/students/{self.student_b_id}/documents",
            ),
        ]

        for method, path in paths:
            response = self.client.request(method, path)
            self.assertEqual(response.status_code, 404, response.text)

        response = self.client.post(
            f"/api/student-knowledge/students/{self.student_b_id}/documents",
            data={
                "source_mode": "pasted_text",
                "chinese_text": "不应该保存",
            },
        )
        self.assertEqual(response.status_code, 404, response.text)

    def test_cross_student_folder_move_is_rejected(self):
        response = self.client.post(
            f"/api/student-knowledge/students/{self.student_a_id}/documents",
            data={
                "title": "学生 A 的资料",
                "source_mode": "pasted_text",
                "chinese_text": "学生 A 的课堂内容。",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        note_id = response.json()["id"]

        response = self.client.post(
            f"/api/student-knowledge/students/{self.student_a_id}"
            "/documents/move",
            json={
                "note_ids": [note_id],
                "folder_id": self.folder_b_id,
            },
        )
        self.assertEqual(response.status_code, 404, response.text)

    def test_record_deletion_is_rejected_and_record_preserved(self):
        response = self.client.post(
            f"/api/student-knowledge/students/{self.student_a_id}/documents",
            data={
                "title": "需要保留的资料",
                "source_mode": "pasted_text",
                "chinese_text": "这条记录必须保留。",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        note_id = response.json()["id"]

        response = self.client.delete(
            f"/api/student-knowledge/students/{self.student_a_id}"
            f"/documents/{note_id}"
        )
        self.assertEqual(response.status_code, 409, response.text)

        response = self.client.get(
            f"/api/student-knowledge/students/{self.student_a_id}/documents"
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["total"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
