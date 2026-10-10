"""Модель данных (CONTRACT 5). Типы обобщённые — одна схема для PostgreSQL 16 и SQLite в тестах."""
from datetime import date, datetime

from sqlalchemy import (JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text,
                        UniqueConstraint, Index)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, utcnow


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16))                      # candidate | employer
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verify_code: Mapped[str | None] = mapped_column(String(6), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    profile: Mapped["CandidateProfile | None"] = relationship(back_populates="user", uselist=False)


class ExternalIdentity(Base):
    """Внешняя учётная запись (сейчас FSP ID). См. CONTEXT.md."""
    __tablename__ = "external_identities"
    __table_args__ = (UniqueConstraint("provider", "subject"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(32))                  # 'fsp'
    subject: Mapped[str] = mapped_column(String(128))
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    claims: Mapped[dict] = mapped_column(JSON, default=dict)


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    telegram: Mapped[str | None] = mapped_column(String(64), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    work_format: Mapped[str | None] = mapped_column(String(16), nullable=True)
    salary_expect_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    spec: Mapped[str | None] = mapped_column(String(32), nullable=True)   # результат опроса по специализации
    skills: Mapped[list] = mapped_column(JSON, default=list)
    roles: Mapped[list] = mapped_column(JSON, default=list)              # роли в команде: «Тимлид», «Разработчик», …
    soft_skills: Mapped[list] = mapped_column(JSON, default=list)
    experience_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    about: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent_pd: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    visible_fields: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="profile")


class VerifiedResult(Base):
    """Подтверждённый результат из источника результатов (не «достижение», см. CONTEXT.md)."""
    __tablename__ = "verified_results"
    __table_args__ = (UniqueConstraint("source", "external_id", "user_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(32))                    # 'fsp'
    external_id: Mapped[str] = mapped_column(String(128))
    event: Mapped[str] = mapped_column(String(255))
    discipline: Mapped[str] = mapped_column(String(255))
    year: Mapped[int] = mapped_column(Integer)
    place: Mapped[int | None] = mapped_column(Integer, nullable=True)
    role: Mapped[str] = mapped_column(String(16))                      # winner | prize | participant
    team: Mapped[bool] = mapped_column(Boolean, default=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class GradeAttempt(Base):
    __tablename__ = "grade_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    spec: Mapped[str] = mapped_column(String(32))
    claimed_grade: Mapped[str] = mapped_column(String(16))
    attempt_no: Mapped[int] = mapped_column(Integer, default=1)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    theta: Mapped[float | None] = mapped_column(Float, nullable=True)
    result: Mapped[str | None] = mapped_column(String(16), nullable=True)   # confirmed | failed
    items: Mapped[dict] = mapped_column(JSON, default=dict)                 # состояние попытки (ответы — только на сервере)


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("user_id", "spec"), Index("ix_categories_spec_grade", "spec", "grade"))
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    spec: Mapped[str] = mapped_column(String(32))
    grade: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))                    # confirmed | unconfirmed | none
    theta: Mapped[float | None] = mapped_column(Float, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suggest_upgrade: Mapped[bool] = mapped_column(Boolean, default=False)


class Employer(Base):
    """Работодатель (в UI «Профиль компании»). Не «организация», см. CONTEXT.md."""
    __tablename__ = "employers"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    inn: Mapped[str | None] = mapped_column(String(12), nullable=True)
    field: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    contacts: Mapped[str | None] = mapped_column(String(512), nullable=True)


class Need(Base):
    """Потребность работодателя; при published=true — вакансия."""
    __tablename__ = "needs"
    __table_args__ = (Index("ix_needs_spec_grade", "spec", "grade"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employers.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    spec: Mapped[str] = mapped_column(String(32))
    grade: Mapped[str] = mapped_column(String(16))
    skills: Mapped[list] = mapped_column(JSON, default=list)          # [{name, weight}]
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    salary_from: Mapped[int] = mapped_column(Integer)
    salary_to: Mapped[int] = mapped_column(Integer)
    salary_type: Mapped[str] = mapped_column(String(8))                # gross | net
    work_format: Mapped[str | None] = mapped_column(String(16), nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Invitation(Base):
    __tablename__ = "invitations"
    id: Mapped[int] = mapped_column(primary_key=True)
    need_id: Mapped[int | None] = mapped_column(ForeignKey("needs.id", ondelete="SET NULL"), nullable=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employers.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    message: Mapped[str] = mapped_column(Text)
    salary_from: Mapped[int] = mapped_column(Integer)
    salary_to: Mapped[int] = mapped_column(Integer)
    salary_type: Mapped[str] = mapped_column(String(8))
    contact_method: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), default="sent")    # sent | viewed | accepted | declined
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Application(Base):
    """Отклик кандидата на вакансию (дополнительный сценарий)."""
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("need_id", "candidate_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    need_id: Mapped[int] = mapped_column(ForeignKey("needs.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="sent")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
