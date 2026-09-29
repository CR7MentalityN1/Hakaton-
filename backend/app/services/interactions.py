from sqlalchemy import update
from app.models import (
    Interaction,
    ITProgram,
    ITProduct,
    Workflow,
    WorkflowStage,
    WorkflowTransition,
    University,
    utcnow,
)
from app.core.errors import fail
from app.core.cache import cache
from app.security.access import (
    require_university,
    require_assignee,
    require_interaction,
)
from app.services.common import snapshot, audit


def validate_input(db, user, p):
    require_university(db, user, p.university_id)
    require_assignee(db, user, p.responsible_employee_id)
    for cls, id in [(ITProgram, p.program_id), (ITProduct, p.product_id)]:
        if not db.get(cls, id):
            fail(422, "REFERENCE_INVALID", "Программа или продукт не найдены")
    wf = db.get(Workflow, p.workflow_id)
    if not wf or not wf.active:
        fail(422, "WORKFLOW_INACTIVE", "Workflow не найден или отключён")
    stages = [s for s in wf.stages if s.active]
    if not stages:
        fail(422, "STAGE_REQUIRED", "Нет активных этапов")
    return stages[0]


def create(db, user, p):
    first = validate_input(db, user, p)
    item = Interaction(**p.model_dump(), current_workflow_stage_id=first.id)
    if user.role == "user":
        item.responsible_employee_id = user.id
    db.add(item)
    db.flush()
    db.add(
        WorkflowTransition(
            interaction_id=item.id,
            from_stage_id=None,
            to_stage_id=first.id,
            changed_by=user.id,
            comment="Создано взаимодействие",
        )
    )
    db.get(University, item.university_id).updated_at = utcnow()
    audit(db, user, "interaction.create", item)
    return item


def edit(db, user, item, p, version):
    if p.university_id != item.university_id or p.workflow_id != item.workflow_id:
        fail(
            409,
            "IDENTITY_IMMUTABLE",
            "Вуз и workflow существующего взаимодействия менять нельзя",
        )
    if (
        p.responsible_employee_id != item.responsible_employee_id
        and user.role == "user"
    ):
        fail(403, "ASSIGNMENT_FORBIDDEN", "Назначение меняет руководитель")
    validate_input(db, user, p)
    old = snapshot(item)
    cas(db, item, version, p.model_dump())
    audit(db, user, "interaction.update", item, old)


def cas(db, item, version, changes):
    # Atomic compare-and-swap also protects API imports from overwriting browser edits.
    result = db.execute(
        update(Interaction)
        .where(Interaction.id == item.id, Interaction.version == version)
        .values(**changes, version=version + 1, updated_at=utcnow())
    )
    if result.rowcount != 1:
        fail(
            409,
            "VERSION_CONFLICT",
            "Данные изменились. Обновите карточку и повторите действие.",
        )
    db.refresh(item)
    db.get(University, item.university_id).updated_at = utcnow()


def allowed_stages(db, user, item):
    wf = db.get(Workflow, item.workflow_id)
    if not wf.active:
        return []
    all_stages = wf.stages
    active = [
        s
        for s in all_stages
        if s.active
        and (user.role == "admin" or user.role in s.allowed_roles)
        and s.id != item.current_workflow_stage_id
    ]
    if user.role in ("admin", "manager"):
        return active
    current = db.get(WorkflowStage, item.current_workflow_stage_id)
    following = [
        s for s in all_stages if s.active and s.order_index > current.order_index
    ]
    allowed = []
    for s in following:
        if s in active:
            allowed.append(s)
        if not s.optional:
            break
    return allowed


def transition(db, user, iid, p):
    item = require_interaction(db, user, iid)
    if p.to_stage_id not in [s.id for s in allowed_stages(db, user, item)]:
        fail(
            403,
            "TRANSITION_FORBIDDEN",
            "Переход на этот этап недоступен для вашей роли",
        )
    old = snapshot(item)
    previous = item.current_workflow_stage_id
    cas(db, item, p.version, {"current_workflow_stage_id": p.to_stage_id})
    db.add(
        WorkflowTransition(
            interaction_id=iid,
            from_stage_id=previous,
            to_stage_id=p.to_stage_id,
            changed_by=user.id,
            comment=p.comment,
        )
    )
    audit(db, user, "interaction.transition", item, old)
    db.commit()
    cache.invalidate()
    return item
