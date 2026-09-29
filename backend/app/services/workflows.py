from sqlalchemy import update
from app.models import Workflow, WorkflowStage
from app.core.errors import fail
from app.core.cache import cache
from app.services.common import audit, snapshot


def save(db, user, p, wid=None):
    wf = db.get(Workflow, wid) if wid else Workflow(name=p.name)
    if wid and not wf:
        fail(404, "NOT_FOUND", "Workflow не найден")
    old = (
        {**snapshot(wf), "stages": [snapshot(stage) for stage in wf.stages]}
        if wid
        else None
    )
    if wid:
        result = db.execute(
            update(Workflow)
            .where(Workflow.id == wid, Workflow.version == p.version)
            .values(
                name=p.name,
                description=p.description,
                active=p.active,
                version=p.version + 1,
            )
        )
        if result.rowcount != 1:
            fail(409, "VERSION_CONFLICT", "Workflow изменён другим пользователем")
    else:
        wf.description = p.description
        wf.active = p.active
        db.add(wf)
        db.flush()
    existing = {s.id: s for s in wf.stages} if wid else {}
    incoming = {s.id for s in p.stages if s.id}
    if not set(existing).issubset(incoming):
        fail(
            409,
            "STAGE_PRESERVE",
            "Этап нельзя удалить. Отключите его, чтобы сохранить историю.",
        )
    for stage in p.stages:
        values = stage.model_dump(exclude={"id"})
        if stage.id:
            if stage.id not in existing:
                fail(422, "STAGE_INVALID", "Этап относится к другому workflow")
            for k, v in values.items():
                setattr(existing[stage.id], k, v)
        else:
            db.add(WorkflowStage(workflow_id=wf.id, **values))
    db.flush()
    db.refresh(wf)
    audit(
        db,
        user,
        "workflow.update" if wid else "workflow.create",
        wf,
        old,
        {**snapshot(wf), "stages": [snapshot(s) for s in wf.stages]},
    )
    db.commit()
    cache.invalidate()
    return wf
