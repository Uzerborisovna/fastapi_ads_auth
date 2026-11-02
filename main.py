# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from models import Base, engine, Session, User, Token, Advertisement, Role
from sqlalchemy import select
import schemas
from auth import check_password, hash_password, check_token, check_object_access
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db_session


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Инициализация ролей и прав
    async with Session() as session:
        roles = await session.scalars(select(Role))
        if not roles.first():
            from scripts import create_initial_roles
            await create_initial_roles(session)

    yield
    print("Shutting down...")
    await engine.dispose()


app = FastAPI(title="Advertisement Service with Auth", lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello from FastAPI with Auth!"}


# --- ЛОГИН ---
@app.post("/login", response_model=schemas.LoginResponse)
async def login(
        login_data: schemas.LoginRequest,
        db_session: AsyncSession = Depends(get_db_session)
):
    query = select(User).where(User.name == login_data.username)
    user = await db_session.scalar(query)

    if user is None or not check_password(login_data.password, user.password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    new_token = Token(user=user)
    db_session.add(new_token)
    await db_session.commit()
    await db_session.refresh(new_token)
    return new_token


# --- ПОЛЬЗОВАТЕЛИ ---
@app.post("/user", response_model=schemas.IdResponse)
async def create_user(
        user_data: schemas.UserCreate,
        db_session: AsyncSession = Depends(get_db_session)
):
    hashed_password = hash_password(user_data.password)
    new_user = User(name=user_data.username, password=hashed_password)

    role_user = await db_session.scalar(select(Role).where(Role.name == "user"))
    if role_user:
        new_user.roles.append(role_user)

    db_session.add(new_user)
    try:
        await db_session.commit()
    except Exception:
        await db_session.rollback()
        raise HTTPException(status_code=400, detail="Username already exists")

    await db_session.refresh(new_user)
    return {"id": new_user.id}


@app.get("/user/{user_id}", response_model=schemas.UserResponse)
async def get_user(
        user_id: int,
        db_session: AsyncSession = Depends(get_db_session)
):
    user = await db_session.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/user/", response_model=list[schemas.UserResponse])
async def get_all_users(
        db_session: AsyncSession = Depends(get_db_session),
        token_obj: Token = Depends(check_token)
):
    users = await db_session.scalars(select(User))
    return users.all()


@app.patch("/user/{user_id}", response_model=schemas.UserResponse)
async def update_user(
        user_id: int,
        user_data: schemas.UserUpdate,
        db_session: AsyncSession = Depends(get_db_session),
        token_obj: Token = Depends(check_token)
):
    user_to_update = await db_session.scalar(select(User).where(User.id == user_id))
    if not user_to_update:
        raise HTTPException(status_code=404, detail="User not found")

    has_access = await check_object_access(
        user=token_obj.user, orm_object=user_to_update, db_session=db_session, need_write=True
    )
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")

    if user_data.username:
        user_to_update.name = user_data.username
    if user_data.password:
        user_to_update.password = hash_password(user_data.password)

    await db_session.commit()
    await db_session.refresh(user_to_update)
    return user_to_update


@app.delete("/user/{user_id}")
async def delete_user(
        user_id: int,
        db_session: AsyncSession = Depends(get_db_session),
        token_obj: Token = Depends(check_token)
):
    user_to_delete = await db_session.scalar(select(User).where(User.id == user_id))
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found")

    has_access = await check_object_access(
        user=token_obj.user, orm_object=user_to_delete, db_session=db_session, need_write=True
    )
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")

    await db_session.delete(user_to_delete)
    await db_session.commit()
    return {"message": "User deleted"}


# --- ОБЪЯВЛЕНИЯ ---
@app.post("/advertisement", response_model=schemas.AdResponse)
async def create_ad(
        ad: schemas.AdCreate,
        token_obj: Token = Depends(check_token),
        db_session: AsyncSession = Depends(get_db_session)
):
    new_ad = Advertisement(
        title=ad.title,
        description=ad.description,
        price=ad.price,
        author_id=token_obj.user_id
    )

    has_access = await check_object_access(
        user=token_obj.user, orm_object=Advertisement, db_session=db_session, need_write=True
    )
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")

    db_session.add(new_ad)
    await db_session.commit()
    await db_session.refresh(new_ad)
    return new_ad


@app.get("/advertisement/{advertisement_id}", response_model=schemas.AdResponse)
async def get_ad(
        advertisement_id: int,
        db_session: AsyncSession = Depends(get_db_session)
):
    ad = await db_session.scalar(select(Advertisement).where(Advertisement.id == advertisement_id))
    if not ad:
        raise HTTPException(status_code=404, detail="Advertisement not found")
    return ad


@app.patch("/advertisement/{advertisement_id}", response_model=schemas.AdResponse)
async def update_ad(
        advertisement_id: int,
        ad_update: schemas.AdUpdate,
        token_obj: Token = Depends(check_token),
        db_session: AsyncSession = Depends(get_db_session)
):
    ad = await db_session.scalar(select(Advertisement).where(Advertisement.id == advertisement_id))
    if not ad:
        raise HTTPException(status_code=404, detail="Advertisement not found")

    has_access = await check_object_access(
        user=token_obj.user, orm_object=ad, db_session=db_session, need_write=True
    )
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")

    update_data = ad_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(ad, key, value)

    await db_session.commit()
    await db_session.refresh(ad)
    return ad


@app.delete("/advertisement/{advertisement_id}")
async def delete_ad(
        advertisement_id: int,
        token_obj: Token = Depends(check_token),
        db_session: AsyncSession = Depends(get_db_session)
):
    ad = await db_session.scalar(select(Advertisement).where(Advertisement.id == advertisement_id))
    if not ad:
        raise HTTPException(status_code=404, detail="Advertisement not found")

    has_access = await check_object_access(
        user=token_obj.user, orm_object=ad, db_session=db_session, need_write=True
    )
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")

    await db_session.delete(ad)
    await db_session.commit()
    return {"message": "Advertisement deleted"}


@app.get("/advertisement", response_model=list[schemas.AdResponse])
async def search_ads(
        title: str | None = None,
        description: str | None = None,
        author_id: int | None = None,
        min_price: float | None = None,
        db_session: AsyncSession = Depends(get_db_session)
):
    query = select(Advertisement)
    if title:
        query = query.where(Advertisement.title.ilike(f"%{title}%"))
    if description:
        query = query.where(Advertisement.description.ilike(f"%{description}%"))
    if author_id:
        query = query.where(Advertisement.author_id == author_id)
    if min_price is not None:
        query = query.where(Advertisement.price >= min_price)

    result = await db_session.execute(query)
    return result.scalars().all()