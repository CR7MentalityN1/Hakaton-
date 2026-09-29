from datetime import datetime, time, timedelta, timezone
from sqlalchemy import select, func, or_
from app.models import (
    Interaction,
    University,
    ITProgram,
    ITDirection,
    ITProduct,
    WorkflowStage,
    Employee,
    UniversityAssignment,
)
from app.security.access import scope_interactions, university_scope
from app.core.errors import fail


def interaction_query(user, filters):
    stmt = (
        select(
            *Interaction.__table__.c,
            University.name.label("university"),
            ITProgram.name.label("program"),
            ITDirection.name.label("direction"),
            ITDirection.id.label("direction_id"),
            ITProduct.name.label("product"),
            ITProduct.vendor.label("vendor"),
            WorkflowStage.name.label("stage"),
            func.coalesce(Employee.full_name, "Не назначен").label("responsible"),
        )
        .join(University, Interaction.university_id == University.id)
        .join(ITProgram, Interaction.program_id == ITProgram.id)
        .join(ITDirection, ITProgram.direction_id == ITDirection.id)
        .join(ITProduct, Interaction.product_id == ITProduct.id)
        .join(WorkflowStage, Interaction.current_workflow_stage_id == WorkflowStage.id)
        .outerjoin(Employee, Interaction.responsible_employee_id == Employee.id)
    )
    stmt = scope_interactions(stmt, user)
    if filters.start and filters.end and filters.start > filters.end:
        fail(422, "PERIOD_INVALID", "Начало периода позже окончания")
    if filters.start:
        stmt = stmt.where(
            Interaction.created_at
            >= datetime.combine(filters.start, time.min, tzinfo=timezone.utc)
        )
    if filters.end:
        stmt = stmt.where(
            Interaction.created_at
            < datetime.combine(
                filters.end + timedelta(days=1), time.min, tzinfo=timezone.utc
            )
        )
    for name, col in [
        ("university_id", Interaction.university_id),
        ("direction_id", ITProgram.direction_id),
        ("program_id", Interaction.program_id),
        ("product_id", Interaction.product_id),
        ("responsible_employee_id", Interaction.responsible_employee_id),
        ("stage_id", Interaction.current_workflow_stage_id),
    ]:
        if getattr(filters, name) is not None:
            stmt = stmt.where(col == getattr(filters, name))
    if filters.q:
        term = "%" + filters.q.replace("%", "\\%").replace("_", "\\_") + "%"
        stmt = stmt.where(
            or_(
                *[
                    c.ilike(term, escape="\\")
                    for c in [
                        University.name,
                        ITProgram.name,
                        ITProduct.name,
                        Interaction.contract_number,
                        Employee.full_name,
                    ]
                ]
            )
        )
    return stmt


def page_rows(db, stmt, page=1, page_size=20, order=None):
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    if order is not None:
        stmt = stmt.order_by(order)
    rows = [
        dict(r)
        for r in db.execute(
            stmt.offset((page - 1) * page_size).limit(page_size)
        ).mappings()
    ]
    return {"items": rows, "total": total, "page": page, "page_size": page_size}


def university_page(
    db,
    user,
    q="",
    city="",
    region="",
    page=1,
    page_size=20,
    sort="name",
    descending=False,
):
    stmt = select(*University.__table__.c)
    if user.role != "admin":
        stmt = stmt.where(University.id.in_(university_scope(user)))
    if q:
        stmt = stmt.where(
            or_(
                University.name.ilike("%" + q + "%"),
                University.short_name.ilike("%" + q + "%"),
            )
        )
    if city:
        stmt = stmt.where(University.city == city)
    if region:
        stmt = stmt.where(University.region == region)
    col = {
        "name": University.name,
        "city": University.city,
        "region": University.region,
        "updated_at": University.updated_at,
    }.get(sort)
    if col is None:
        fail(422, "SORT_INVALID", "Недопустимая колонка сортировки")
    result = page_rows(
        db, stmt, page, page_size, col.desc() if descending else col.asc()
    )
    enrich_universities(db, result["items"])
    return result


def enrich_universities(db, rows):
    ids = [r["id"] for r in rows]
    if not ids:
        return
    counts = {
        r[0]: (r[1], r[2])
        for r in db.execute(
            select(
                Interaction.university_id,
                func.count(func.distinct(Interaction.program_id)),
                func.count(func.distinct(Interaction.product_id)),
            )
            .where(Interaction.university_id.in_(ids))
            .group_by(Interaction.university_id)
        )
    }
    managers = {}
    statuses = {}
    for uid, eid, name in db.execute(
        select(UniversityAssignment.university_id, Employee.id, Employee.full_name)
        .join(Employee, UniversityAssignment.employee_id == Employee.id)
        .where(UniversityAssignment.university_id.in_(ids))
    ):
        managers.setdefault(uid, []).append({"id": eid, "full_name": name})
    for uid, name in db.execute(
        select(Interaction.university_id, WorkflowStage.name)
        .join(WorkflowStage, Interaction.current_workflow_stage_id == WorkflowStage.id)
        .where(Interaction.university_id.in_(ids))
        .distinct()
    ):
        statuses.setdefault(uid, []).append(name)
    for row in rows:
        row.update(
            managers=managers.get(row["id"], []),
            program_count=counts.get(row["id"], (0, 0))[0],
            product_count=counts.get(row["id"], (0, 0))[1],
            statuses=statuses.get(row["id"], []),
        )
