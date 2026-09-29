from datetime import datetime, timezone, date
from sqlalchemy import (
    String,
    Text,
    ForeignKey,
    UniqueConstraint,
    Index,
    JSON,
    DateTime,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


def utcnow():
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(primary_key=True)
    keycloak_user_id: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(250))
    email: Mapped[str] = mapped_column(String(250), unique=True)
    role: Mapped[str] = mapped_column(String(20), default="user")
    active: Mapped[bool] = mapped_column(default=True)
    manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id"), index=True
    )
    __table_args__ = (
        CheckConstraint("role IN ('user','manager','admin')", name="employee_role"),
    )


class University(Base, TimestampMixin):
    __tablename__ = "universities"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(250), unique=True)
    short_name: Mapped[str] = mapped_column(String(100), default="")
    city: Mapped[str] = mapped_column(String(150), index=True)
    region: Mapped[str] = mapped_column(String(150), index=True)


class UniversityAssignment(Base):
    __tablename__ = "university_assignments"
    university_id: Mapped[int] = mapped_column(
        ForeignKey("universities.id", ondelete="CASCADE"), primary_key=True
    )
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id"), primary_key=True, index=True
    )


class ITDirection(Base):
    __tablename__ = "it_directions"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")


class ITProgram(Base):
    __tablename__ = "it_programs"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(250), unique=True)
    direction_id: Mapped[int] = mapped_column(
        ForeignKey("it_directions.id"), index=True
    )
    description: Mapped[str] = mapped_column(Text, default="")


class ITProduct(Base):
    __tablename__ = "it_products"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(250), unique=True)
    vendor: Mapped[str] = mapped_column(String(250))
    description: Mapped[str] = mapped_column(Text, default="")


class UniversityContact(Base):
    __tablename__ = "university_contacts"
    id: Mapped[int] = mapped_column(primary_key=True)
    university_id: Mapped[int] = mapped_column(
        ForeignKey("universities.id", ondelete="CASCADE"), index=True
    )
    full_name: Mapped[str] = mapped_column(String(250))
    position: Mapped[str] = mapped_column(String(250), default="")
    email: Mapped[str] = mapped_column(String(250), default="")
    phone: Mapped[str] = mapped_column(String(100), default="")


class Workflow(Base):
    __tablename__ = "workflows"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(250))
    description: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(default=True)
    version: Mapped[int] = mapped_column(default=1)
    stages: Mapped[list["WorkflowStage"]] = relationship(
        order_by="WorkflowStage.order_index", lazy="selectin"
    )


class WorkflowStage(Base):
    __tablename__ = "workflow_stages"
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflows.id"), index=True)
    name: Mapped[str] = mapped_column(String(250))
    description: Mapped[str] = mapped_column(Text, default="")
    order_index: Mapped[int]
    active: Mapped[bool] = mapped_column(default=True)
    optional: Mapped[bool] = mapped_column(default=False)
    allowed_roles: Mapped[list] = mapped_column(
        JSON, default=lambda: ["user", "manager", "admin"]
    )


class Interaction(Base, TimestampMixin):
    __tablename__ = "interactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    university_id: Mapped[int] = mapped_column(
        ForeignKey("universities.id"), index=True
    )
    program_id: Mapped[int] = mapped_column(ForeignKey("it_programs.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("it_products.id"), index=True)
    responsible_employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id"), index=True
    )
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflows.id"), index=True)
    current_workflow_stage_id: Mapped[int] = mapped_column(
        ForeignKey("workflow_stages.id"), index=True
    )
    contract_number: Mapped[str] = mapped_column(String(250), default="")
    license_signed: Mapped[bool] = mapped_column(default=False)
    license_start_date: Mapped[date | None]
    license_end_date: Mapped[date | None]
    transfer_status: Mapped[str] = mapped_column(String(200), default="В работе")
    notes: Mapped[str] = mapped_column(Text, default="")
    applications: Mapped[int] = mapped_column(default=0)
    students: Mapped[int] = mapped_column(default=0)
    streams: Mapped[int] = mapped_column(default=0)
    version: Mapped[int] = mapped_column(default=1)
    source: Mapped[str | None] = mapped_column(String(30))
    external_id: Mapped[str | None] = mapped_column(String(250))
    __table_args__ = (
        UniqueConstraint("source", "external_id"),
        Index("ix_interaction_period_university", "created_at", "university_id"),
        CheckConstraint(
            "applications >= 0 AND students >= 0 AND streams >= 0",
            name="positive_statistics",
        ),
    )


class WorkflowTransition(Base):
    __tablename__ = "workflow_transitions"
    id: Mapped[int] = mapped_column(primary_key=True)
    interaction_id: Mapped[int] = mapped_column(
        ForeignKey("interactions.id", ondelete="CASCADE"), index=True
    )
    from_stage_id: Mapped[int | None] = mapped_column(ForeignKey("workflow_stages.id"))
    to_stage_id: Mapped[int] = mapped_column(ForeignKey("workflow_stages.id"))
    changed_by: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    interaction_id: Mapped[int] = mapped_column(
        ForeignKey("interactions.id", ondelete="CASCADE"), index=True
    )
    stage_id: Mapped[int] = mapped_column(ForeignKey("workflow_stages.id"))
    author_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class Attachment(Base):
    __tablename__ = "attachments"
    id: Mapped[int] = mapped_column(primary_key=True)
    interaction_id: Mapped[int] = mapped_column(
        ForeignKey("interactions.id", ondelete="CASCADE"), index=True
    )
    stage_id: Mapped[int] = mapped_column(ForeignKey("workflow_stages.id"))
    original_filename: Mapped[str] = mapped_column(String(250))
    stored_filename: Mapped[str] = mapped_column(String(100), unique=True)
    mime_type: Mapped[str] = mapped_column(String(150))
    size: Mapped[int]
    sha256: Mapped[str] = mapped_column(String(64))
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(200))
    old_value: Mapped[dict | None] = mapped_column(JSON)
    new_value: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


class AppSetting(Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
