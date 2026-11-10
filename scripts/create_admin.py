from getpass import getpass

from pwdlib import PasswordHash
from sqlalchemy.exc import IntegrityError

from backend.database import SessionLocal
from backend.auth_models import User, Role, UserRole


password_hash = PasswordHash.recommended()


def main():
    db = SessionLocal()

    try:
        # 只允许通过此脚本创建第一个管理员
        existing_admin = (
            db.query(UserRole)
            .join(Role, UserRole.role_id == Role.id)
            .filter(Role.name == "admin")
            .first()
        )

        if existing_admin:
            print("已有管理员账号，停止创建。")
            return

        username = input("请输入管理员用户名：").strip()

        if not username:
            print("用户名不能为空。")
            return

        if len(username) > 100:
            print("用户名不能超过 100 个字符。")
            return

        if db.query(User).filter(User.username == username).first():
            print("该用户名已经存在。")
            return

        email = input("请输入邮箱（可留空）：").strip() or None

        if email and len(email) > 255:
            print("邮箱不能超过 255 个字符。")
            return

        if email and db.query(User).filter(User.email == email).first():
            print("该邮箱已经被使用。")
            return

        password = getpass("请输入管理员密码（至少 12 个字符）：")

        if len(password) < 12:
            print("密码至少需要 12 个字符。")
            return

        if len(password.encode("utf-8")) > 1024:
            print("密码过长，请使用更短的密码。")
            return

        password_confirm = getpass("请再次输入管理员密码：")

        if password != password_confirm:
            print("两次密码不一致。")
            return

        admin_role = db.query(Role).filter(Role.name == "admin").first()

        if not admin_role:
            print("数据库中没有 admin 角色，请先初始化角色。")
            return

        user = User(
            username=username,
            email=email,
            hashed_password=password_hash.hash(password),
            is_active=True,
        )

        db.add(user)
        db.flush()

        db.add(
            UserRole(
                user_id=user.id,
                role_id=admin_role.id,
            )
        )

        db.commit()

        print("\n管理员账号创建成功。")
        print("用户 ID：", user.id)
        print("用户名：", user.username)
        print("角色：admin")
        print("密码：未显示，也未保存明文。")

    except IntegrityError:
        db.rollback()
        print("创建失败：用户名或邮箱可能已被其他记录使用。")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
