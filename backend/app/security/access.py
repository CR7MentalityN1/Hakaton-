from sqlalchemy import select, or_
from app.models import Employee, University, UniversityAssignment, Interaction
from app.core.errors import fail


def team_ids(user):
    return select(Employee.id).where(
        or_(Employee.id == user.id, Employee.manager_id == user.id)
        if user.role == "manager"
        else Employee.id == user.id
    )


def university_scope(user):
    if user.role == "admin":
        return select(University.id)
    return select(UniversityAssignment.university_id).where(
        UniversityAssignment.employee_id.in_(team_ids(user))
    )


def scope_interactions(statement, user):
    if user.role != "admin":
        statement = statement.where(
            or_(
                Interaction.university_id.in_(university_scope(user)),
                Interaction.responsible_employee_id.in_(team_ids(user)),
            )
        )
    return statement


def require_university(db, user, uid):
    # The same university predicate is applied to CRUD, exports, files and integrations.
    query = select(University).where(University.id == uid)
    if user.role != "admin":
        query = query.where(University.id.in_(university_scope(user)))
    obj = db.scalar(query)
    if not obj:
        fail(404, "NOT_FOUND", "Вуз не найден или недоступен")
    return obj


def require_interaction(db, user, iid):
    obj = db.scalar(
        scope_interactions(select(Interaction).where(Interaction.id == iid), user)
    )
    if not obj:
        fail(404, "NOT_FOUND", "Взаимодействие не найдено или недоступно")
    return obj


def require_assignee(db, user, eid):
    if eid is None:
        return
    e = db.get(Employee, eid)
    if not e or not e.active:
        fail(422, "EMPLOYEE_INVALID", "Ответственный не найден или отключён")
    if user.role == "user" and eid != user.id:
        fail(403, "ASSIGNMENT_FORBIDDEN", "Нельзя назначить другого сотрудника")
    if user.role == "manager" and e.id != user.id and e.manager_id != user.id:
        fail(403, "ASSIGNMENT_FORBIDDEN", "Сотрудник не входит в вашу команду")
