import os
import unittest

os.environ["JWT_SECRET_KEY"] = "student-auth-isolated-test-secret"
os.environ["JWT_ALGORITHM"] = "HS256"

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.database import Base, get_db
from backend.auth_models import User
from backend.student_profile_models import Student
from backend.student_auth_models import StudentAuthAccount
from backend.student_auth_routes import router

from backend import auth_routes


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

event.listen(
    engine,
    "connect",
    lambda conn, rec: conn.execute("PRAGMA foreign_keys=ON"),
)

TestingSession = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)

# 只创建认证测试必需的三张表，不创建其他业务表。
Base.metadata.create_all(
    engine,
    tables=[
        User.__table__,
        Student.__table__,
        StudentAuthAccount.__table__,
    ],
)

active_teacher = {"id": None}

app = FastAPI()
app.include_router(router)


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


def override_teacher():
    with TestingSession() as db:
        return db.query(User).filter(
            User.id == active_teacher["id"]
        ).one()


app.dependency_overrides[get_db] = override_db
app.dependency_overrides[auth_routes.get_current_teacher] = override_teacher


class StudentAuthTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with TestingSession.begin() as db:
            teacher1 = User(
                username="teacher_test_1",
                hashed_password="not-used",
            )
            teacher2 = User(
                username="teacher_test_2",
                hashed_password="not-used",
            )
            db.add_all([teacher1, teacher2])
            db.flush()

            student1 = Student(
                teacher_user_id=teacher1.id,
                display_name="测试学生一",
                is_active=1,
            )
            student2 = Student(
                teacher_user_id=teacher2.id,
                display_name="测试学生二",
                is_active=1,
            )
            db.add_all([student1, student2])
            db.flush()

            cls.teacher1_id = teacher1.id
            cls.teacher2_id = teacher2.id
            cls.student1_id = student1.id
            cls.student2_id = student2.id

        active_teacher["id"] = cls.teacher1_id
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)
        engine.dispose()

    def check(self, condition, message):
        self.assertTrue(condition, message)
        print("PASS:", message)

    def test_complete_student_auth_flow(self):
        # 1. 教师创建学生账号
        response = self.client.post(
            f"/api/student-auth/students/{self.student1_id}/account",
            json={},
        )
        self.assertEqual(response.status_code, 200, response.text)

        created = response.json()
        username = created["login_username"]
        temporary_password = created["temporary_password"]

        self.check(
            created["must_change_password"] is True,
            "新账号要求首次登录修改密码",
        )

        with TestingSession() as db:
            account = db.query(StudentAuthAccount).filter(
                StudentAuthAccount.student_id == self.student1_id
            ).one()

            self.check(
                account.hashed_password != temporary_password,
                "数据库只保存密码哈希，不保存明文",
            )

        # 2. 错误密码不能登录
        response = self.client.post(
            "/api/student-auth/login",
            json={
                "username": username,
                "password": "wrong-password",
            },
        )
        self.assertEqual(response.status_code, 401)
        print("PASS: 错误密码登录被拒绝")

        # 3. 正确密码登录
        response = self.client.post(
            "/api/student-auth/login",
            json={
                "username": username,
                "password": temporary_password,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)

        token = response.json()["access_token"]
        self.check(
            response.json()["must_change_password"] is True,
            "首次登录返回修改密码标记",
        )

        student_headers = {
            "Authorization": f"Bearer {token}"
        }

        # 4. 学生只能取得自己的身份资料
        response = self.client.get(
            "/api/student-auth/me",
            headers=student_headers,
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["id"], self.student1_id)
        self.assertEqual(
            response.json()["display_name"],
            "测试学生一",
        )
        print("PASS: 学生读取自己的资料")

        # 5. 教师 Token 不能冒充学生 Token
        teacher_token = auth_routes.create_access_token(
            self.teacher1_id
        )
        response = self.client.get(
            "/api/student-auth/me",
            headers={
                "Authorization": f"Bearer {teacher_token}"
            },
        )
        self.assertEqual(response.status_code, 401)
        print("PASS: 教师 Token 被学生接口拒绝")

        # 6. 学生修改首次密码
        new_password = "NewStudentPassword2026"
        response = self.client.post(
            "/api/student-auth/change-password",
            json={
                "current_password": temporary_password,
                "new_password": new_password,
            },
            headers=student_headers,
        )
        self.assertEqual(response.status_code, 200, response.text)
        print("PASS: 学生成功修改密码")

        response = self.client.get(
            "/api/student-auth/me",
            headers=student_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.check(
            response.json()["must_change_password"] is False,
            "修改后首次登录标记已清除",
        )

        # 7. 旧密码失效
        response = self.client.post(
            "/api/student-auth/login",
            json={
                "username": username,
                "password": temporary_password,
            },
        )
        self.assertEqual(response.status_code, 401)
        print("PASS: 修改后旧密码失效")

        # 8. 新密码有效
        response = self.client.post(
            "/api/student-auth/login",
            json={
                "username": username,
                "password": new_password,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        print("PASS: 新密码可以登录")

        # 9. 其他教师不能管理该学生账号
        active_teacher["id"] = self.teacher2_id

        response = self.client.post(
            f"/api/student-auth/students/{self.student1_id}/account/reset-password"
        )
        self.assertEqual(response.status_code, 404)
        print("PASS: 其他教师不能重置该学生密码")

        # 10. 原教师可以重置密码
        active_teacher["id"] = self.teacher1_id

        response = self.client.post(
            f"/api/student-auth/students/{self.student1_id}/account/reset-password"
        )
        self.assertEqual(response.status_code, 200, response.text)

        reset_password = response.json()["temporary_password"]
        self.check(
            response.json()["must_change_password"] is True,
            "教师重置密码后重新要求首次修改",
        )

        response = self.client.post(
            "/api/student-auth/login",
            json={
                "username": username,
                "password": reset_password,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        print("PASS: 重置后的临时密码可以登录")

        # 11. 停用学生账号后，已有 Token 也不能继续使用
        with TestingSession.begin() as db:
            account = db.query(StudentAuthAccount).filter(
                StudentAuthAccount.student_id == self.student1_id
            ).one()
            account.is_active = False

        response = self.client.get(
            "/api/student-auth/me",
            headers=student_headers,
        )
        self.assertEqual(response.status_code, 401)
        print("PASS: 停用账号后旧 Token 失效")


if __name__ == "__main__":
    unittest.main(verbosity=2)
