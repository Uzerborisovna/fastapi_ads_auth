
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import DB_URL
import uuid
import datetime
from sqlalchemy import String, ForeignKey, Uuid, DateTime, Boolean, Table, Column, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from typing import Literal, List

engine = create_async_engine(DB_URL)
Session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

ModelName = Literal["User", "Advertisement"]

user_role_relation = Table(
    "user_role_relation", Base.metadata,
    Column("user_id", ForeignKey("todo_user.id"), primary_key=True),
    Column("role_id", ForeignKey("role.id"), primary_key=True)
)

role_right_relation = Table(
    "role_right_relation", Base.metadata,
    Column("role_id", ForeignKey("role.id"), primary_key=True),
    Column("right_id", ForeignKey("right.id"), primary_key=True)
)

class Right(Base):
    __tablename__ = "right"
    id: Mapped[int] = mapped_column(primary_key=True)
    write: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    only_own: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    model: Mapped[ModelName] = mapped_column(String(50), nullable=False)

class Role(Base):
    __tablename__ = "role"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    rights: Mapped[List[Right]] = relationship(secondary=role_right_relation, lazy="joined")

class User(Base):
    __tablename__ = "todo_user"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String(70), nullable=False)
    tokens: Mapped[list["Token"]] = relationship("Token", back_populates="user", cascade="all, delete-orphan", lazy="joined")
    roles: Mapped[List[Role]] = relationship(secondary=user_role_relation, lazy="joined")

class Token(Base):
    __tablename__ = "token"
    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[uuid.UUID] = mapped_column(Uuid, server_default=func.gen_random_uuid(), unique=True, nullable=False)
    creation_time: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("todo_user.id"))
    user: Mapped[User] = relationship(User, back_populates="tokens", lazy="joined")

class Advertisement(Base):
    __tablename__ = "advertisements"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("todo_user.id"), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    author: Mapped[User] = relationship(User, lazy="joined")