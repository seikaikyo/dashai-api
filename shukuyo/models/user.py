"""使用者模型 - Clerk 認證 + Neon 持久化"""
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from datetime import datetime, date as date_type
from typing import Optional
import uuid


class User(SQLModel, table=True):
    """使用者（對應 Clerk user）"""
    __tablename__ = "users"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    clerk_id: str = Field(unique=True, index=True, max_length=100)
    email: Optional[str] = Field(default=None, max_length=255)
    display_name: Optional[str] = Field(default=None, max_length=100)
    birth_date: Optional[date_type] = Field(default=None)
    plan: str = Field(default="free", max_length=20)  # free | credits | monthly
    credits_remaining: int = Field(default=0)
    preferences: dict = Field(default_factory=dict, sa_column=Column(JSON, default={}))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    partners: list["UserPartner"] = Relationship(back_populates="user")
    companies: list["UserCompany"] = Relationship(back_populates="user")


class UserPartner(SQLModel, table=True):
    """收藏對象"""
    __tablename__ = "user_partners"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    nickname: str = Field(max_length=50)
    birth_date: date_type
    relation: str = Field(max_length=20)  # dating | spouse | parent | family | friend | master
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional[User] = Relationship(back_populates="partners")


class CompanyCache(SQLModel, table=True):
    """公司資料快取（全域共用，查過的設立日期不用再查 GCIS）"""
    __tablename__ = "company_cache"

    id: str = Field(
        sa_column=Column(PG_UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())),
    )
    name: str = Field(max_length=200, index=True)
    country: str = Field(default="tw", max_length=5)
    founding_date: Optional[date_type] = Field(default=None)
    business_no: Optional[str] = Field(default=None, max_length=20)
    source: Optional[str] = Field(default=None, max_length=50)  # gcis / gbizinfo / opencorporates / manual
    job_url_104: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserCompany(SQLModel, table=True):
    """收藏公司"""
    __tablename__ = "user_companies"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    name: str = Field(max_length=200)
    founding_date: date_type
    country: str = Field(default="tw", max_length=5)
    memo: Optional[str] = Field(default=None, max_length=500)
    job_url: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional[User] = Relationship(back_populates="companies")
