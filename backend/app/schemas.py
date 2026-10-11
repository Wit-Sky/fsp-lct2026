"""Pydantic-схемы запросов и ответов API (они же — OpenAPI /api/docs)."""
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

Role = Literal["candidate", "employer"]
Spec = Literal["backend", "frontend", "bas"]
Grade = Literal["junior", "middle", "senior"]
WorkFormat = Literal["office", "remote", "hybrid"]
SalaryType = Literal["gross", "net"]
Status = Literal["sent", "viewed", "accepted", "declined"]


class Orm(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------- auth
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4, max_length=128)
    role: Role


class RegisterOut(BaseModel):
    user_id: int
    email: str
    verify_code: str | None = Field(None, description="Только в демо-режиме: имитация письма с кодом")
    message: str


class VerifyIn(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role
    user_id: int


# ---------------------------------------------------------------- профиль кандидата
class ResultOut(Orm):
    id: int | None = None
    source: str
    external_id: str
    event: str
    discipline: str
    year: int
    place: int | None = None
    role: Literal["winner", "prize", "participant"]
    team: bool = False


class ProfileIn(BaseModel):
    full_name: str | None = None
    birth_date: date | None = None
    phone: str | None = None
    telegram: str | None = None
    city: str | None = None
    work_format: WorkFormat | None = None
    salary_expect_from: int | None = Field(None, ge=0)
    spec: Spec | None = None
    skills: list[str] | None = None
    roles: list[str] | None = Field(None, description="Роли в команде (например, «Тимлид», «Разработчик»)")
    soft_skills: list[str] | None = None
    experience_years: float | None = Field(None, ge=0, le=60)
    about: str | None = None
    consent_pd: bool | None = None
    parent_consent: bool | None = None
    fsp_skipped: bool = Field(False, description="Кандидат выбрал продолжить без истории ФСП")
    visible_fields: dict[str, bool] | None = Field(None, description="Что видно работодателю: full_name, city, birth_date, about, experience_years, results")


class ProfileOut(BaseModel):
    user_id: int
    email: str
    full_name: str
    birth_date: date | None
    phone: str | None
    telegram: str | None
    city: str | None
    work_format: str | None
    salary_expect_from: int | None
    spec: str | None
    skills: list[str]
    roles: list[str] = []
    soft_skills: list[str] = []
    experience_years: float | None
    about: str | None
    consent_pd: bool
    parent_consent: bool
    visible_fields: dict[str, bool]
    minor: bool
    published: bool = Field(description="Профиль виден работодателям (согласие на ПД; для младше 18 — согласие родителя)")
    fsp_linked: bool
    fsp_id: str | None
    fsp_skipped: bool


class FspStartOut(BaseModel):
    authorize_url: str = Field(description="Переход с одноразовым кодом; основной JWT в URL не передаётся")
    expires_in: int = Field(description="Срок действия кода в секундах")


class ResumeDraft(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    telegram: str | None = None
    experience_years: float | None = None
    skills: list[str] = []
    roles: list[str] = []
    soft_skills: list[str] = []
    spec: str | None = None
    claimed_grade: str | None = None
    text_chars: int = 0


class ResultsOut(BaseModel):
    sources: dict[str, list[ResultOut]]
    fsp_linked: bool
    fsp_score: float
    explain: list[dict]


# ---------------------------------------------------------------- тестирование и категория
class TestStartIn(BaseModel):
    spec: Spec
    claimed_grade: Grade


class ItemOut(BaseModel):
    item_id: str
    template_id: str
    text: str
    code: str | None = None
    kind: Literal["single", "number", "order"]
    options: list[str] | None = None
    topic: str
    no: int
    total: int


class TestStateOut(BaseModel):
    attempt_id: int
    spec: str
    claimed_grade: str
    item: ItemOut | None
    finished: bool
    answered: int
    total: int
    deadline: datetime
    item_time_limit_sec: int
    result: dict | None = None


class AnswerIn(BaseModel):
    item_id: str
    answer: Any = Field(description="single: текст варианта или индекс; number: число; order: список вариантов или индексов")


class TestResultOut(BaseModel):
    attempt_id: int
    spec: str
    claimed_grade: str
    theta: float
    grade: str | None
    confirmed: bool
    suggest_upgrade: bool
    correct: int
    total: int
    unanswered: int = Field(0, description="Сколько заданий осталось без ответа (время вышло); входят в total и считаются неверными")
    topics: list[dict]
    category: dict | None
    next_attempt_at: datetime | None
    started_at: datetime
    finished_at: datetime | None


class AttemptOut(BaseModel):
    id: int
    spec: str
    claimed_grade: str
    started_at: datetime
    finished_at: datetime | None
    theta: float | None
    result: str | None


class CategoryOut(BaseModel):
    spec: str | None
    grade: str | None
    status: Literal["confirmed", "unconfirmed", "none"]
    theta: float | None
    percentile: float | None
    confirmed_at: datetime | None
    tested_at: datetime | None
    next_attempt_at: datetime | None
    suggest_upgrade: bool
    can_retest: dict[str, datetime | None] = Field(description="Для каждого грейда: когда можно пройти тест (null — сейчас)")
    attempts: list[AttemptOut]


# ---------------------------------------------------------------- работодатель
class EmployerIn(BaseModel):
    name: str | None = None
    inn: str | None = Field(None, pattern=r"^\d{10}(\d{2})?$")
    field: str | None = None
    description: str | None = None
    contacts: str | None = None


class EmployerOut(Orm):
    id: int
    name: str
    inn: str | None
    field: str | None
    description: str | None
    contacts: str | None


class SkillWeight(BaseModel):
    name: str
    weight: float = Field(1, gt=0, le=5)


class NeedIn(BaseModel):
    title: str = Field(min_length=2)
    spec: Spec
    grade: Grade
    skills: list[SkillWeight] = []
    description: str | None = None
    salary_from: int = Field(gt=0, description="Рубли")
    salary_to: int = Field(gt=0, description="Рубли")
    salary_type: SalaryType
    work_format: WorkFormat | None = None
    published: bool = False

    @model_validator(mode="after")
    def _salary(self):
        if self.salary_from > self.salary_to:
            raise ValueError("salary_from must be <= salary_to")
        return self


class NeedOut(Orm):
    id: int
    employer_id: int
    title: str
    spec: str
    grade: str
    skills: list[dict]
    description: str | None
    salary_from: int
    salary_to: int
    salary_type: str
    work_format: str | None
    published: bool
    created_at: datetime


class NeedCreated(NeedOut):
    search_id: int


class VacancyOut(NeedOut):
    company: str
    applied: bool = False


class CategoryCount(BaseModel):
    spec: str
    grade: str
    target: bool
    total: int
    confirmed: int
    with_fsp: int


class ExplainItem(BaseModel):
    factor: str
    weight: float | None = None
    value: float | None = None
    text: str


class CandidateCard(BaseModel):
    id: int
    full_name: str | None
    city: str | None
    birth_date: date | None = None
    minor: bool
    about: str | None
    experience_years: float | None
    work_format: str | None
    salary_expect_from: int | None
    spec: str | None
    skills: list[str]
    roles: list[str] = []
    soft_skills: list[str] = []
    grade: str | None
    status: str
    theta: float | None
    percentile: float | None
    tested_at: datetime | None
    results: list[ResultOut]
    has_fsp: bool
    email: str | None
    phone: str | None
    telegram: str | None
    contacts_hidden: bool
    invitation_status: str | None = None


class MatchOut(BaseModel):
    candidate_id: int
    score: float
    explain: list[ExplainItem]
    candidate: CandidateCard


class MatchesOut(BaseModel):
    need_id: int
    search_id: int
    filters: dict
    total: int
    items: list[MatchOut]


class InvitationIn(BaseModel):
    candidate_id: int
    need_id: int | None = None
    message: str = Field(min_length=1)
    salary_from: int = Field(gt=0, description="Рубли")
    salary_to: int = Field(gt=0, description="Рубли")
    salary_type: SalaryType
    contact_method: str = Field(min_length=1, description="Как работодатель свяжется: телефон, Telegram, email и т. п.")

    @model_validator(mode="after")
    def _salary(self):
        if self.salary_from > self.salary_to:
            raise ValueError("salary_from must be <= salary_to")
        return self


class InvitationOut(BaseModel):
    id: int
    need_id: int | None
    need_title: str | None
    employer_id: int
    company: str
    candidate_id: int
    candidate_name: str | None = None
    message: str
    salary_from: int
    salary_to: int
    salary_type: str
    contact_method: str
    status: Status
    created_at: datetime
    updated_at: datetime
    candidate_contacts: dict | None = Field(None, description="Только работодателю и только после принятия")


class ApplyIn(BaseModel):
    message: str | None = None


class ApplicationOut(BaseModel):
    id: int
    need_id: int
    need_title: str
    company: str
    candidate_id: int
    candidate: CandidateCard | None = None
    message: str | None
    status: Status
    created_at: datetime
    updated_at: datetime
    salary_from: int
    salary_to: int
    salary_type: str


class ApplicationStatusIn(BaseModel):
    status: Literal["viewed", "accepted", "declined"]


# ---------------------------------------------------------------- регулярные задания

TaskKind = Literal["solve", "approach"]


class TaskIn(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    text: str = Field(min_length=10, description="Условие: задача или ситуация, к которой нужно предложить подход")
    spec: Spec
    grade: Grade | None = Field(None, description="Для какого грейда; пусто — для всех грейдов специализации")
    kind: TaskKind = Field("solve", description="solve — решить; approach — предложить подход к решению")


class TaskOut(BaseModel):
    id: int
    title: str
    text: str
    spec: str
    grade: str | None
    kind: str
    active: bool
    company: str
    created_at: datetime
    answers: int = 0


class TaskAnswerIn(BaseModel):
    answer: str = Field(min_length=10, max_length=5000)


class TaskReviewIn(BaseModel):
    rating: int = Field(ge=0, le=3, description="0 — не решено, 1 — частично, 2 — хорошо, 3 — отлично")
    feedback: str | None = Field(None, max_length=2000)


class TaskAnswerOut(BaseModel):
    id: int
    task_id: int
    task_title: str
    candidate_id: int
    candidate_name: str | None = None
    candidate_grade: str | None = None
    answer: str
    rating: int | None
    feedback: str | None
    created_at: datetime
    reviewed_at: datetime | None


class MyTasksOut(BaseModel):
    offered: list[TaskOut] = Field(description="Предложенные задания по специализации кандидата, на которые он ещё не ответил")
    answered: list[TaskAnswerOut]
    hint: str | None = None
