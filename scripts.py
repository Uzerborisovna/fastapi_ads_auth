
import asyncio
from sqlalchemy import select
from models import Session, User, Role, Right
from auth import hash_password


async def create_initial_roles(session):
    """Создает базовые роли и права"""

    # --- Права для объявлений ---
    # Чтение любых объявлений
    right_read_any_ad = Right(read=True, write=False, only_own=False, model="Advertisement")
    # Чтение и запись своих объявлений
    right_rw_own_ad = Right(read=True, write=True, only_own=True, model="Advertisement")
    # Любые действия с любыми объявлениями (для админа)
    right_full_ad = Right(read=True, write=True, only_own=False, model="Advertisement")

    # --- Права для пользователей ---
    # Чтение и запись своего профиля
    right_rw_own_user = Right(read=True, write=True, only_own=True, model="User")
    # Любые действия с любыми пользователями (для админа)
    right_full_user = Right(read=True, write=True, only_own=False, model="User")

    session.add_all([
        right_read_any_ad, right_rw_own_ad, right_full_ad,
        right_rw_own_user, right_full_user
    ])
    await session.flush()

    # --- Роли ---
    role_user = Role(name="user")
    role_user.rights = [right_read_any_ad, right_rw_own_ad, right_rw_own_user]

    role_admin = Role(name="admin")
    role_admin.rights = [right_full_ad, right_full_user]

    session.add_all([role_user, role_admin])
    await session.commit()
    print("Initial roles and rights created.")


async def main():
    async with Session() as session:
        result = await session.execute(select(Role))
        existing_roles = result.scalars().all()
        if not existing_roles:
            await create_initial_roles(session)
        else:
            print("Roles already exist.")


if __name__ == "__main__":
    asyncio.run(main())