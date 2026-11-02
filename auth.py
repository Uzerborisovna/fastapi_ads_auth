
import bcrypt
import uuid
import datetime
from fastapi import Header, HTTPException, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Token, Session as DbSession
from models import User, Role, Right, user_role_relation, role_right_relation
from config import TOKEN_TTL
from sqlalchemy.sql import func
from database import get_db_session

# Создаем объект для заголовка безопасности, чтобы FastAPI показал замочек в /docs
token_header = APIKeyHeader(name="x-token", auto_error=True)

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()

def check_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed_password.encode())

async def check_token(
    token: uuid.UUID = Depends(token_header),
    db_session: AsyncSession = Depends(get_db_session)
) -> Token:
    expire_threshold = func.now() - datetime.timedelta(seconds=TOKEN_TTL)

    query = select(Token).where(
        Token.token == token,
        Token.creation_time >= expire_threshold
    )
    token_obj = await db_session.scalar(query)

    if token_obj is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return token_obj

async def check_object_access(
    user: User,
    orm_object,
    db_session: AsyncSession,
    need_read: bool = False,
    need_write: bool = False,
) -> bool:
    model_class = orm_object if isinstance(orm_object, type) else orm_object.__class__
    model_name = model_class.__name__

    where_args = [
        User.id == user.id,
        Right.model == model_name
    ]
    if need_read:
        where_args.append(Right.read == True)
    if need_write:
        where_args.append(Right.write == True)

    # Если объект имеет поле author_id (наше объявление) и это не сам пользователь
    if not isinstance(orm_object, type) and hasattr(orm_object, 'author_id'):
        if orm_object.author_id != user.id:
            where_args.append(Right.only_own == False)

    query = (
        select(func.count())
        .select_from(User)
        .join(user_role_relation, User.id == user_role_relation.c.user_id)
        .join(Role, user_role_relation.c.role_id == Role.id)
        .join(role_right_relation, Role.id == role_right_relation.c.role_id)
        .join(Right, role_right_relation.c.right_id == Right.id)
        .where(*where_args)
    )

    result = await db_session.execute(query)
    count = result.scalar()
    return count > 0