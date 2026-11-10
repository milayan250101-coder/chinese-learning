from getpass import getpass
from pwdlib import PasswordHash

from backend.database import SessionLocal
from backend.auth_models import User, Role, UserRole

db = SessionLocal()

try:
    teacher_role = db.query(Role).filter(
        Role.name == "teacher"
    ).first()

    if not teacher_role:
        raise SystemExit("错误：没有找到 teacher 角色。")

    existing_teacher = (
        db.query(User)
        .join(UserRole, UserRole.user_id == User.id)
        .filter(UserRole.role_id == teacher_role.id)
        .first()
    )

    if existing_teacher:
        raise SystemExit("已经存在教师账号，不再创建。")

    print("=== 创建初始教师账号 ===")

    username = input("请输入教师用户名：").strip()
    email = input("请输入邮箱（可以留空）：").strip() or None

    if not username:
        raise SystemExit("用户名不能为空。")

    if db.query(User).filter(User.username == username).first():
        raise SystemExit("用户名已经存在。")

    if email and db.query(User).filter(User.email == email).first():
        raise SystemExit("邮箱已经存在。")

    password = getpass("请输入登录密码（至少12位）：")
    confirmation = getpass("请再次输入密码：")

    if len(password) < 12:
        raise SystemExit("密码至少需要12位。")

    if password != confirmation:
        raise SystemExit("两次密码不一致。")

    user = User(
        username=username,
        email=email,
        hashed_password=PasswordHash.recommended().hash(password),
        is_active=True,
    )

    db.add(user)
    db.flush()

    db.add(UserRole(
        user_id=user.id,
        role_id=teacher_role.id,
    ))

    db.commit()

    print("\n教师账号创建成功！")
    print("用户ID：", user.id)
    print("用户名：", user.username)
    print("角色：teacher")
    print("密码没有显示。")

except Exception:
    db.rollback()
    raise

finally:
    db.close()
