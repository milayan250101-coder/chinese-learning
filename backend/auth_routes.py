import os
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth_models import User, Role, UserRole


router = APIRouter(prefix="/api/auth", tags=["Teacher Authentication"])

password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login"
)

ACCESS_TOKEN_EXPIRE_MINUTES = 60


def get_jwt_config():
    secret = os.getenv("JWT_SECRET_KEY")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")

    if not secret:
        raise RuntimeError("JWT_SECRET_KEY is not configured.")

    return secret, algorithm


def get_user_roles(db: Session, user_id: int):
    rows = (
        db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user_id)
        .all()
    )

    return [row[0] for row in rows]


def create_access_token(user_id: int):
    secret, algorithm = get_jwt_config()

    now = datetime.now(timezone.utc)
    expires = now + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expires,
    }

    token = jwt.encode(
        payload,
        secret,
        algorithm=algorithm,
    )

    return token


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    secret, algorithm = get_jwt_config()

    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired login token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[algorithm],
        )

        user_id = payload.get("sub")

        if not user_id:
            raise credentials_error

        user_id = int(user_id)

    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise credentials_error

    user = db.query(User).filter(User.id == user_id).first()

    if not user or not user.is_active:
        raise credentials_error

    return user


def get_current_teacher(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = get_user_roles(db, user.id)

    if "teacher" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher access required.",
        )

    return user


@router.post("/login")
def teacher_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.username == form_data.username)
        .first()
    )

    if not user or not password_hash.verify(
        form_data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
        )

    roles = get_user_roles(db, user.id)

    if "teacher" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account does not have teacher access.",
        )

    token = create_access_token(user.id)

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.get("/me")
def read_current_teacher(
    user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "roles": get_user_roles(db, user.id),
    }
