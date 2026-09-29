from datetime import date, datetime
from typing import Generic, TypeVar, Literal, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator


class DTO(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, extra="forbid", str_strip_whitespace=True
    )


class ErrorOut(BaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class Ok(DTO):
    ok: bool = True


class EmployeeOut(DTO):
    id: int
    keycloak_user_id: str
    full_name: str
    email: str
    role: Literal["user", "manager", "admin"]
    active: bool
    manager_id: int | None


class EmployeeInput(DTO):
    keycloak_user_id: str = Field(min_length=1, max_length=200)
    full_name: str = Field(min_length=1, max_length=250)
    email: str = Field(
        min_length=3, max_length=250, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    )
    role: Literal["user", "manager", "admin"] = "user"
    active: bool = True
    manager_id: int | None = None


class UniversityInput(DTO):
    name: str = Field(min_length=1, max_length=250)
    short_name: str = Field(default="", max_length=100)
    city: str = Field(min_length=1, max_length=150)
    region: str = Field(default="", max_length=150)


class UniversityOut(UniversityInput):
    id: int
    created_at: datetime
    updated_at: datetime
    managers: list[dict[str, Any]] = Field(default_factory=list)
    program_count: int = 0
    product_count: int = 0
    statuses: list[str] = Field(default_factory=list)


class AssignmentInput(DTO):
    employee_ids: list[int] = Field(max_length=50)


class ContactInput(DTO):
    full_name: str = Field(min_length=1, max_length=250)
    position: str = Field(default="", max_length=250)
    email: str = Field(default="", max_length=250)
    phone: str = Field(default="", max_length=100)


class ContactOut(ContactInput):
    id: int
    university_id: int


class DirectionInput(DTO):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)


class DirectionOut(DirectionInput):
    id: int


class ProgramInput(DirectionInput):
    direction_id: int


class ProgramOut(ProgramInput):
    id: int


class ProductInput(DirectionInput):
    vendor: str = Field(min_length=1, max_length=250)


class ProductOut(ProductInput):
    id: int


class StageInput(DTO):
    id: int | None = None
    name: str = Field(min_length=1, max_length=250)
    description: str = Field(default="", max_length=5000)
    order_index: int = Field(ge=0)
    active: bool = True
    optional: bool = False
    allowed_roles: list[Literal["user", "manager", "admin"]] = Field(
        default_factory=lambda: ["user", "manager", "admin"], min_length=1
    )


class StageOut(StageInput):
    id: int
    workflow_id: int


class WorkflowInput(DTO):
    name: str = Field(min_length=1, max_length=250)
    description: str = Field(default="", max_length=5000)
    active: bool = True
    version: int = 1
    stages: list[StageInput] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def valid_stages(self):
        if len({s.order_index for s in self.stages}) != len(self.stages):
            raise ValueError("Порядок этапов должен быть уникален")
        ids = [s.id for s in self.stages if s.id is not None]
        if len(set(ids)) != len(ids):
            raise ValueError("Этапы не могут повторяться")
        if self.active and not any(s.active for s in self.stages):
            raise ValueError("Нужен хотя бы один активный этап")
        return self


class WorkflowOut(DTO):
    id: int
    name: str
    description: str
    active: bool
    version: int
    stages: list[StageOut]


class InteractionInput(DTO):
    university_id: int
    program_id: int
    product_id: int
    responsible_employee_id: int | None = None
    workflow_id: int
    contract_number: str = Field(default="", max_length=250)
    license_signed: bool = False
    license_start_date: date | None = None
    license_end_date: date | None = None
    transfer_status: str = Field(default="В работе", max_length=200)
    notes: str = Field(default="", max_length=10000)
    applications: int = Field(default=0, ge=0, le=10000000)
    students: int = Field(default=0, ge=0, le=10000000)
    streams: int = Field(default=0, ge=0, le=100000)

    @model_validator(mode="after")
    def dates(self):
        if (
            self.license_start_date
            and self.license_end_date
            and self.license_end_date < self.license_start_date
        ):
            raise ValueError("Окончание лицензии раньше начала")
        return self


class InteractionOut(InteractionInput):
    id: int
    current_workflow_stage_id: int
    version: int
    created_at: datetime
    updated_at: datetime
    university: str
    program: str
    direction: str
    direction_id: int
    product: str
    vendor: str
    stage: str
    responsible: str
    source: str | None = None
    external_id: str | None = None


class TransitionInput(DTO):
    to_stage_id: int
    version: int
    comment: str = Field(default="", max_length=10000)


class TransitionOut(DTO):
    id: int
    interaction_id: int
    from_stage_id: int | None
    to_stage_id: int
    changed_by: int
    comment: str
    created_at: datetime
    actor: str
    from_stage: str | None
    to_stage: str


class CommentInput(DTO):
    stage_id: int
    text: str = Field(min_length=1, max_length=10000)


class CommentOut(CommentInput):
    id: int
    interaction_id: int
    author_id: int
    created_at: datetime
    actor: str


class AttachmentOut(DTO):
    id: int
    interaction_id: int
    stage_id: int
    original_filename: str
    mime_type: str
    size: int
    sha256: str
    uploaded_by: int
    uploaded_at: datetime


class Filters(DTO):
    start: date | None = None
    end: date | None = None
    university_id: int | None = None
    direction_id: int | None = None
    program_id: int | None = None
    product_id: int | None = None
    responsible_employee_id: int | None = None
    stage_id: int | None = None
    q: str = Field(default="", max_length=200)


class ReportInput(Filters):
    columns: list[str] = Field(
        default_factory=lambda: [
            "university",
            "direction",
            "program",
            "product",
            "stage",
            "responsible",
            "contract_number",
            "license_end_date",
        ],
        min_length=1,
        max_length=20,
    )
    format: Literal["xlsx", "xls", "pdf", "json"] = "xlsx"


class ReportPreview(DTO):
    columns: dict[str, str]
    items: list[dict[str, Any]]
    total: int


class ImportPreview(DTO):
    headers: list[str]
    rows: list[dict[str, Any]]
    total: int


class OperationResult(DTO):
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[dict[str, Any]] = Field(default_factory=list)


class DashboardOut(DTO):
    universities: int
    interactions: int
    programs: int
    products: int
    applications: int
    students: int
    streams: int
    by_status: list[dict[str, Any]]
    by_direction: list[dict[str, Any]]
    by_product: list[dict[str, Any]]
    dynamics: list[dict[str, Any]]
    by_manager: list[dict[str, Any]]
    ranking: list[dict[str, Any]]


class AuditOut(DTO):
    id: int
    user_id: int | None
    action: str
    entity_type: str
    entity_id: str
    old_value: dict | None
    new_value: dict | None
    created_at: datetime


class SettingsInput(DTO):
    organization: str = Field(min_length=1, max_length=250)
    retention_days: int = Field(ge=1, le=3650)


class AdviceOut(DTO):
    provider: str
    suggestions: list[str]
