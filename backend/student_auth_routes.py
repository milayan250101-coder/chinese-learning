import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth_routes import get_current_teacher, get_jwt_config
from backend.auth_models import User
from backend.student_profile_models import Student
from backend.student_auth_models import StudentAuthAccount
from backend.student_routes import get_owned_student


router = APIRouter(
    prefix="/api/student-auth",
    tags=["Student Authentication"],
)

password_hash = PasswordHash.recommended()

student_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/student-auth/login"
)

STUDENT_TOKEN_EXPIRE_MINUTES = 60


def get_student_signing_key():
    secret, algorithm = get_jwt_config()
    derived = hashlib.sha256(
        (secret + ":student-auth-v1").encode("utf-8")
    ).digest()
    return derived, algorithm


def create_student_access_token(student_id: int):
    secret, algorithm = get_student_signing_key()

    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(student_id),
        "token_type": "student",
        "iat": now,
        "exp": now + timedelta(
            minutes=STUDENT_TOKEN_EXPIRE_MINUTES
        ),
    }

    return jwt.encode(payload, secret, algorithm=algorithm)


def get_current_student(
    token: str = Depends(student_oauth2_scheme),
    db: Session = Depends(get_db),
):
    secret, algorithm = get_student_signing_key()

    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired student login token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[algorithm],
        )

        if payload.get("token_type") != "student":
            raise credentials_error

        student_id = int(payload.get("sub"))

    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise credentials_error

    account = (
        db.query(StudentAuthAccount)
        .filter(
            StudentAuthAccount.student_id == student_id,
            StudentAuthAccount.is_active.is_(True),
        )
        .first()
    )

    if not account:
        raise credentials_error

    student = (
        db.query(Student)
        .filter(
            Student.id == student_id,
            Student.is_active == 1,
        )
        .first()
    )

    if not student:
        raise credentials_error

    return student, account


class StudentLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)


class StudentChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class StudentAccountCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    initial_password: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
    )


def generate_login_username(student_id: int) -> str:
    return f"stu-{student_id}-{secrets.token_hex(3)}"


def generate_temporary_password() -> str:
    return secrets.token_urlsafe(12)


@router.post("/login")
def student_login(
    data: StudentLoginRequest,
    db: Session = Depends(get_db),
):
    account = (
        db.query(StudentAuthAccount)
        .filter(
            StudentAuthAccount.login_username == data.username.strip()
        )
        .first()
    )

    if (
        not account
        or not account.is_active
        or not password_hash.verify(
            data.password,
            account.hashed_password,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
        )

    student = (
        db.query(Student)
        .filter(
            Student.id == account.student_id,
            Student.is_active == 1,
        )
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This student account is inactive.",
        )

    account.last_login_at = datetime.utcnow()
    db.commit()

    return {
        "access_token": create_student_access_token(student.id),
        "token_type": "bearer",
        "expires_in": STUDENT_TOKEN_EXPIRE_MINUTES * 60,
        "must_change_password": account.must_change_password,
    }


@router.get("/me")
def read_current_student(
    identity=Depends(get_current_student),
):
    student, account = identity

    return {
        "id": student.id,
        "display_name": student.display_name,
        "login_username": account.login_username,
        "must_change_password": account.must_change_password,
    }


@router.post("/change-password")
def change_student_password(
    data: StudentChangePasswordRequest,
    identity=Depends(get_current_student),
    db: Session = Depends(get_db),
):
    student, account = identity

    if not password_hash.verify(
        data.current_password,
        account.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    if data.current_password == data.new_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New password must be different.",
        )

    account.hashed_password = password_hash.hash(data.new_password)
    account.must_change_password = False

    db.commit()

    return {"message": "Password changed successfully."}


@router.post("/students/{student_id}/account")
def create_student_account(
    student_id: int,
    data: StudentAccountCreateRequest,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    student = get_owned_student(db, student_id, teacher.id)

    if student.is_active != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create an account for an inactive student.",
        )

    existing = (
        db.query(StudentAuthAccount)
        .filter(StudentAuthAccount.student_id == student.id)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This student already has a login account.",
        )

    temporary_password = (
        data.initial_password or generate_temporary_password()
    )

    account = StudentAuthAccount(
        student_id=student.id,
        login_username=generate_login_username(student.id),
        hashed_password=password_hash.hash(temporary_password),
        is_active=True,
        must_change_password=True,
    )

    db.add(account)

    try:
        db.commit()
        db.refresh(account)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not create the student account.",
        )

    return {
        "id": account.id,
        "student_id": student.id,
        "login_username": account.login_username,
        "temporary_password": temporary_password,
        "is_active": account.is_active,
        "must_change_password": account.must_change_password,
    }


@router.get("/students/{student_id}/account")
def get_student_account(
    student_id: int,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    student = get_owned_student(db, student_id, teacher.id)

    account = (
        db.query(StudentAuthAccount)
        .filter(StudentAuthAccount.student_id == student.id)
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student login account not found.",
        )

    return {
        "id": account.id,
        "student_id": account.student_id,
        "login_username": account.login_username,
        "is_active": account.is_active,
        "must_change_password": account.must_change_password,
        "last_login_at": account.last_login_at,
        "created_at": account.created_at,
    }


@router.post("/students/{student_id}/account/reset-password")
def reset_student_password(
    student_id: int,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    student = get_owned_student(db, student_id, teacher.id)

    account = (
        db.query(StudentAuthAccount)
        .filter(StudentAuthAccount.student_id == student.id)
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student login account not found.",
        )

    temporary_password = generate_temporary_password()

    account.hashed_password = password_hash.hash(temporary_password)
    account.must_change_password = True
    account.is_active = bool(student.is_active)

    db.commit()

    return {
        "student_id": student.id,
        "login_username": account.login_username,
        "temporary_password": temporary_password,
        "must_change_password": True,
    }
