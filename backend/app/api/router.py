import json
import hashlib
from io import BytesIO
from typing import Annotated
from fastapi import APIRouter, Depends, Query, File, UploadFile, Form, Response
from fastapi.responses import FileResponse
from sqlalchemy import select, delete
from sqlalchemy.orm import Session, aliased
import openpyxl
from app.db.session import get_db
from app.core.config import settings
from app.core.errors import fail
from app.core.cache import cache
from app.models import (
    University,
    UniversityAssignment,
    UniversityContact,
    ITDirection,
    ITProgram,
    ITProduct,
    Employee,
    Workflow,
    WorkflowStage,
    Interaction,
    WorkflowTransition,
    Comment,
    Attachment,
    AuditLog,
    AppSetting,
)
from app.schemas import dto as s
from app.security.auth import current_user, admin_user, manager_user
from app.security.access import (
    require_university,
    require_interaction,
    require_assignee,
    team_ids,
)
from app.repositories.queries import (
    interaction_query,
    page_rows,
    university_page,
    enrich_universities,
)
from app.services import interactions, workflows
from app.services.common import audit, snapshot
from app.services.dashboard import dashboard
from app.services.storage import storage, validate_file
from app.services.ai import assistant
from app.services.importing import read_excel, import_rows, IMPORT_FIELDS
from app.integrations.clients import get_client
from app.reports.rendering import selected_rows, export, chart, COLUMNS, MIMES

ERRORS = {
    code: {"model": s.ErrorOut, "description": description}
    for code, description in [
        (400, "Некорректный запрос"),
        (401, "Необходима авторизация / токен истёк"),
        (403, "Недостаточно прав"),
        (404, "Ресурс не найден или недоступен"),
        (409, "Конфликт версии или зависимых данных"),
        (413, "Превышен лимит размера"),
        (415, "Неподдерживаемый тип файла"),
        (422, "Ошибка валидации"),
        (500, "Внутренняя ошибка сервера"),
        (503, "Зависимый сервис недоступен"),
    ]
}
router = APIRouter(prefix="/api/v1", responses=ERRORS)
DB = Annotated[Session, Depends(get_db)]
User = Annotated[Employee, Depends(current_user)]
Admin = Annotated[Employee, Depends(admin_user)]
Manager = Annotated[Employee, Depends(manager_user)]
PageNumber = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=1000)]


def commit(db):
    db.commit()
    cache.invalidate()


@router.get(
    "/auth/config",
    tags=["Авторизация"],
    summary="Публичные параметры Keycloak",
    response_model=dict[str, str],
)
def auth_config():
    return {
        "url": settings.keycloak_issuer.split("/realms/")[0],
        "realm": "rostelecom-it-school",
        "clientId": settings.keycloak_client_id,
    }


@router.get(
    "/auth/me",
    tags=["Авторизация"],
    summary="Текущий пользователь и актуальные права",
    response_model=s.EmployeeOut,
)
def me(user: User):
    return user


@router.get(
    "/universities",
    tags=["ВУЗы"],
    summary="ВУЗы: поиск, область доступа, сортировка и пагинация",
    response_model=s.Page[s.UniversityOut],
)
def universities(
    db: DB,
    user: User,
    q: str = "",
    city: str = "",
    region: str = "",
    page: PageNumber = 1,
    page_size: PageSize = 20,
    sort: str = "name",
    descending: bool = False,
):
    return university_page(db, user, q, city, region, page, page_size, sort, descending)


@router.post(
    "/universities",
    tags=["ВУЗы"],
    summary="Создать учебное заведение (администратор)",
    response_model=s.UniversityOut,
    status_code=201,
)
def create_university(p: s.UniversityInput, db: DB, user: Admin):
    obj = University(**p.model_dump())
    db.add(obj)
    db.flush()
    audit(db, user, "university.create", obj)
    commit(db)
    return obj


@router.get(
    "/universities/{uid}",
    tags=["ВУЗы"],
    summary="Основные сведения и агрегаты карточки ВУЗа",
    response_model=s.UniversityOut,
)
def university(uid: int, db: DB, user: User):
    obj = require_university(db, user, uid)
    rows = [snapshot(obj)]
    enrich_universities(db, rows)
    return rows[0]


@router.put(
    "/universities/{uid}",
    tags=["ВУЗы"],
    summary="Редактировать ВУЗ (администратор)",
    response_model=s.UniversityOut,
)
def update_university(uid: int, p: s.UniversityInput, db: DB, user: Admin):
    obj = require_university(db, user, uid)
    old = snapshot(obj)
    for k, v in p.model_dump().items():
        setattr(obj, k, v)
    audit(db, user, "university.update", obj, old)
    commit(db)
    return obj


@router.delete(
    "/universities/{uid}",
    tags=["ВУЗы"],
    summary="Удалить ВУЗ без связанных взаимодействий",
    response_model=s.Ok,
)
def delete_university(uid: int, db: DB, user: Admin):
    obj = require_university(db, user, uid)
    audit(db, user, "university.delete", obj, snapshot(obj), {})
    db.delete(obj)
    commit(db)
    return s.Ok()


@router.put(
    "/universities/{uid}/assignments",
    tags=["ВУЗы"],
    summary="Назначить, сменить или снять ответственных",
    response_model=s.Ok,
    description="Руководитель управляет своей командой, администратор — всеми. Пустой список снимает назначение. Права проверяются без Redis-кэша.",
)
def assign_university(uid: int, p: s.AssignmentInput, db: DB, user: Manager):
    obj = require_university(db, user, uid)
    for eid in p.employee_ids:
        require_assignee(db, user, eid)
    previous = list(
        db.scalars(
            select(UniversityAssignment.employee_id).where(
                UniversityAssignment.university_id == uid
            )
        )
    )
    db.execute(
        delete(UniversityAssignment).where(UniversityAssignment.university_id == uid)
    )
    for eid in set(p.employee_ids):
        db.add(UniversityAssignment(university_id=uid, employee_id=eid))
    audit(
        db,
        user,
        "university.assign",
        obj,
        {"employees": previous},
        {"employees": p.employee_ids},
    )
    commit(db)
    return s.Ok()


@router.get(
    "/universities/{uid}/contacts",
    tags=["Контакты"],
    summary="Ответственные от ВУЗа",
    response_model=list[s.ContactOut],
)
def contacts(uid: int, db: DB, user: User):
    require_university(db, user, uid)
    return db.scalars(
        select(UniversityContact).where(UniversityContact.university_id == uid)
    ).all()


@router.post(
    "/universities/{uid}/contacts",
    tags=["Контакты"],
    summary="Добавить контакт в доступный ВУЗ",
    response_model=s.ContactOut,
    status_code=201,
)
def create_contact(uid: int, p: s.ContactInput, db: DB, user: User):
    require_university(db, user, uid)
    obj = UniversityContact(university_id=uid, **p.model_dump())
    db.add(obj)
    db.flush()
    audit(db, user, "contact.create", obj)
    commit(db)
    return obj


@router.put(
    "/universities/{uid}/contacts/{cid}",
    tags=["Контакты"],
    summary="Редактировать контакт доступного ВУЗа",
    response_model=s.ContactOut,
)
def edit_contact(uid: int, cid: int, p: s.ContactInput, db: DB, user: User):
    require_university(db, user, uid)
    obj = db.get(UniversityContact, cid)
    if not obj or obj.university_id != uid:
        fail(404, "NOT_FOUND", "Контакт не найден")
    old = snapshot(obj)
    for k, v in p.model_dump().items():
        setattr(obj, k, v)
    audit(db, user, "contact.update", obj, old)
    commit(db)
    return obj


@router.delete(
    "/universities/{uid}/contacts/{cid}",
    tags=["Контакты"],
    summary="Удалить контакт",
    response_model=s.Ok,
)
def remove_contact(uid: int, cid: int, db: DB, user: Manager):
    require_university(db, user, uid)
    obj = db.get(UniversityContact, cid)
    if not obj or obj.university_id != uid:
        fail(404, "NOT_FOUND", "Контакт не найден")
    audit(db, user, "contact.delete", obj, snapshot(obj), {})
    db.delete(obj)
    commit(db)
    return s.Ok()


def register_catalog(path, model, input_type, output_type, title):
    def listing(
        db: DB, user: User, q: str = "", page: PageNumber = 1, page_size: PageSize = 20
    ):
        key = cache.key(path, {"q": q, "page": page, "size": page_size})
        result = cache.get(key)
        if result is None:
            stmt = select(*model.__table__.c)
            if q:
                stmt = stmt.where(model.name.ilike("%" + q + "%"))
            result = page_rows(db, stmt, page, page_size, model.name)
            cache.set(key, result)
        return result

    def create_item(p: input_type, db: DB, user: Admin):
        if model is ITProgram and not db.get(ITDirection, p.direction_id):
            fail(422, "REFERENCE_INVALID", "Направление не найдено")
        obj = model(**p.model_dump())
        db.add(obj)
        db.flush()
        audit(db, user, path + ".create", obj)
        commit(db)
        return obj

    def get_item(cid: int, db: DB, user: User):
        obj = db.get(model, cid)
        if not obj:
            fail(404, "NOT_FOUND", "Запись не найдена")
        return obj

    def edit_item(cid: int, p: input_type, db: DB, user: Admin):
        obj = get_item(cid, db, user)
        old = snapshot(obj)
        if model is ITProgram and not db.get(ITDirection, p.direction_id):
            fail(422, "REFERENCE_INVALID", "Направление не найдено")
        for k, v in p.model_dump().items():
            setattr(obj, k, v)
        audit(db, user, path + ".update", obj, old)
        commit(db)
        return obj

    def delete_item(cid: int, db: DB, user: Admin):
        obj = get_item(cid, db, user)
        audit(db, user, path + ".delete", obj, snapshot(obj), {})
        db.delete(obj)
        commit(db)
        return s.Ok()

    for method, suffix, fn, response, label in [
        ("GET", "", listing, s.Page[output_type], "Список с пагинацией"),
        ("POST", "", create_item, output_type, "Создание"),
        ("GET", "/{cid}", get_item, output_type, "Карточка"),
        ("PUT", "/{cid}", edit_item, output_type, "Редактирование"),
        ("DELETE", "/{cid}", delete_item, s.Ok, "Удаление неиспользуемой записи"),
    ]:
        router.add_api_route(
            "/" + path + suffix,
            fn,
            methods=[method],
            response_model=response,
            status_code=201 if method == "POST" else 200,
            tags=[title],
            summary=title + ": " + label,
            name=path + "_" + fn.__name__,
            description="Чтение доступно авторизованным пользователям. Изменения разрешены только администратору. Связанные данные защищены внешними ключами. Кэш инвалидируется после успешного изменения.",
        )


register_catalog(
    "directions", ITDirection, s.DirectionInput, s.DirectionOut, "ИТ-направления"
)
register_catalog("programs", ITProgram, s.ProgramInput, s.ProgramOut, "ИТ-программы")
register_catalog("products", ITProduct, s.ProductInput, s.ProductOut, "ИТ-продукты")


@router.get(
    "/users",
    tags=["Пользователи"],
    summary="Сотрудники с учётом командной иерархии",
    response_model=s.Page[s.EmployeeOut],
)
def users(
    db: DB, user: User, page: PageNumber = 1, page_size: PageSize = 20, q: str = ""
):
    stmt = select(*Employee.__table__.c)
    if user.role != "admin":
        stmt = stmt.where(Employee.id.in_(team_ids(user)))
    if q:
        stmt = stmt.where(Employee.full_name.ilike("%" + q + "%"))
    return page_rows(db, stmt, page, page_size, Employee.full_name)


def validate_employee(db, user, p, eid=None):
    if eid == user.id and (p.role != "admin" or not p.active):
        fail(
            409,
            "SELF_LOCKOUT",
            "Нельзя заблокировать собственный административный доступ",
        )
    if p.manager_id:
        manager = db.get(Employee, p.manager_id)
        if not manager or manager.role not in ("manager", "admin") or manager.id == eid:
            fail(422, "MANAGER_INVALID", "Руководитель не найден или недопустим")


@router.post(
    "/users",
    tags=["Пользователи"],
    summary="Зарегистрировать сотрудника по Keycloak subject",
    response_model=s.EmployeeOut,
    status_code=201,
    description="Паролями управляет только Keycloak. Укажите sub уже созданного пользователя realm; при первом входе сотрудник также создаётся автоматически.",
)
def create_user(p: s.EmployeeInput, db: DB, user: Admin):
    validate_employee(db, user, p)
    obj = Employee(**p.model_dump())
    db.add(obj)
    db.flush()
    audit(db, user, "employee.create", obj)
    commit(db)
    return obj


@router.put(
    "/users/{eid}",
    tags=["Пользователи"],
    summary="Изменить роль, руководителя или блокировку сотрудника",
    response_model=s.EmployeeOut,
)
def update_user(eid: int, p: s.EmployeeInput, db: DB, user: Admin):
    obj = db.get(Employee, eid)
    if not obj:
        fail(404, "NOT_FOUND", "Сотрудник не найден")
    validate_employee(db, user, p, eid)
    old = snapshot(obj)
    if p.keycloak_user_id != obj.keycloak_user_id:
        fail(
            409,
            "SUBJECT_IMMUTABLE",
            "Keycloak subject существующего сотрудника менять нельзя",
        )
    for k, v in p.model_dump().items():
        setattr(obj, k, v)
    audit(db, user, "employee.update", obj, old)
    commit(db)
    return obj


@router.get(
    "/workflows",
    tags=["Workflow"],
    summary="Шаблоны и упорядоченные этапы",
    response_model=list[s.WorkflowOut],
)
def workflow_list(db: DB, user: User):
    return db.scalars(select(Workflow).order_by(Workflow.id)).all()


@router.post(
    "/workflows",
    tags=["Workflow"],
    summary="Создать workflow с произвольными этапами",
    response_model=s.WorkflowOut,
    status_code=201,
)
def workflow_create(p: s.WorkflowInput, db: DB, user: Admin):
    return workflows.save(db, user, p)


@router.put(
    "/workflows/{wid}",
    tags=["Workflow"],
    summary="Изменить этапы, порядок, доступные роли и активность",
    response_model=s.WorkflowOut,
    description="Текущая version защищает от потерянных обновлений. Этапы не удаляются физически: active=false сохраняет историю. Идентификаторы существующих этапов обязательны.",
)
def workflow_edit(wid: int, p: s.WorkflowInput, db: DB, user: Admin):
    return workflows.save(db, user, p, wid)


@router.get(
    "/interactions",
    tags=["Взаимодействия"],
    summary="Фильтры, поиск, сортировка и серверная пагинация",
    response_model=s.Page[s.InteractionOut],
    description="Период применяется к дате создания взаимодействия, обе даты включены. Все фильтры объединяются AND. Неподчинённые/неназначенные записи скрыты на уровне SQL.",
)
def interaction_list(
    db: DB,
    user: User,
    f: Annotated[s.Filters, Depends()],
    page: PageNumber = 1,
    page_size: PageSize = 20,
    sort: str = "updated_at",
    descending: bool = True,
):
    col = {
        "updated_at": Interaction.updated_at,
        "created_at": Interaction.created_at,
        "university": University.name,
        "program": ITProgram.name,
        "product": ITProduct.name,
    }.get(sort)
    if col is None:
        fail(422, "SORT_INVALID", "Недопустимая сортировка")
    return page_rows(
        db,
        interaction_query(user, f),
        page,
        page_size,
        col.desc() if descending else col.asc(),
    )


def interaction_out(db, user, iid):
    row = (
        db.execute(interaction_query(user, s.Filters()).where(Interaction.id == iid))
        .mappings()
        .first()
    )
    if not row:
        fail(404, "NOT_FOUND", "Взаимодействие недоступно")
    return dict(row)


@router.get(
    "/interactions/{iid}",
    tags=["Взаимодействия"],
    summary="Карточка доступного взаимодействия",
    response_model=s.InteractionOut,
)
def interaction_get(iid: int, db: DB, user: User):
    return interaction_out(db, user, iid)


@router.post(
    "/interactions",
    tags=["Взаимодействия"],
    summary="Создать взаимодействие на первом активном этапе",
    response_model=s.InteractionOut,
    status_code=201,
)
def interaction_create(p: s.InteractionInput, db: DB, user: User):
    obj = interactions.create(db, user, p)
    commit(db)
    return interaction_out(db, user, obj.id)


@router.put(
    "/interactions/{iid}",
    tags=["Взаимодействия"],
    summary="Изменить реквизиты и показатели с проверкой версии",
    response_model=s.InteractionOut,
)
def interaction_edit(iid: int, p: s.InteractionInput, db: DB, user: User, version: int):
    obj = require_interaction(db, user, iid)
    interactions.edit(db, user, obj, p, version)
    commit(db)
    return interaction_out(db, user, iid)


@router.delete(
    "/interactions/{iid}",
    tags=["Взаимодействия"],
    summary="Удалить взаимодействие и его историю (администратор)",
    response_model=s.Ok,
)
def interaction_delete(iid: int, db: DB, user: Admin):
    obj = require_interaction(db, user, iid)
    files = list(
        db.scalars(
            select(Attachment.stored_filename).where(Attachment.interaction_id == iid)
        )
    )
    audit(db, user, "interaction.delete", obj, snapshot(obj), {})
    db.delete(obj)
    commit(db)
    for key in files:
        storage.delete(key)
    return s.Ok()


@router.get(
    "/interactions/{iid}/allowed-stages",
    tags=["Workflow"],
    summary="Допустимые переходы для текущей роли",
    response_model=list[s.StageOut],
)
def allowed(iid: int, db: DB, user: User):
    return interactions.allowed_stages(db, user, require_interaction(db, user, iid))


@router.post(
    "/interactions/{iid}/transition",
    tags=["Workflow"],
    summary="Перейти на этап и сохранить from/to/actor/time/comment",
    response_model=s.InteractionOut,
)
def change_stage(iid: int, p: s.TransitionInput, db: DB, user: User):
    interactions.transition(db, user, iid, p)
    return interaction_out(db, user, iid)


@router.get(
    "/interactions/{iid}/timeline",
    tags=["Workflow"],
    summary="История переходов с названиями и авторами",
    response_model=list[s.TransitionOut],
)
def timeline(iid: int, db: DB, user: User):
    require_interaction(db, user, iid)
    before = aliased(WorkflowStage)
    after = aliased(WorkflowStage)
    query = (
        select(
            *WorkflowTransition.__table__.c,
            Employee.full_name.label("actor"),
            before.name.label("from_stage"),
            after.name.label("to_stage"),
        )
        .join(Employee, Employee.id == WorkflowTransition.changed_by)
        .outerjoin(before, before.id == WorkflowTransition.from_stage_id)
        .join(after, after.id == WorkflowTransition.to_stage_id)
        .where(WorkflowTransition.interaction_id == iid)
        .order_by(WorkflowTransition.id.desc())
    )
    return [dict(r) for r in db.execute(query).mappings()]


def stage_belongs(db, item, stage_id):
    stage = db.get(WorkflowStage, stage_id)
    if not stage or stage.workflow_id != item.workflow_id:
        fail(422, "STAGE_INVALID", "Этап не относится к workflow взаимодействия")


@router.get(
    "/interactions/{iid}/comments",
    tags=["Комментарии"],
    summary="Комментарии с авторами",
    response_model=list[s.CommentOut],
)
def comments(iid: int, db: DB, user: User):
    require_interaction(db, user, iid)
    return [
        dict(r)
        for r in db.execute(
            select(*Comment.__table__.c, Employee.full_name.label("actor"))
            .join(Employee, Employee.id == Comment.author_id)
            .where(Comment.interaction_id == iid)
            .order_by(Comment.id.desc())
        ).mappings()
    ]


@router.post(
    "/interactions/{iid}/comments",
    tags=["Комментарии"],
    summary="Добавить комментарий к этапу",
    response_model=s.CommentOut,
    status_code=201,
)
def comment_create(iid: int, p: s.CommentInput, db: DB, user: User):
    obj = require_interaction(db, user, iid)
    stage_belongs(db, obj, p.stage_id)
    comment = Comment(interaction_id=iid, author_id=user.id, **p.model_dump())
    db.add(comment)
    db.flush()
    audit(db, user, "comment.create", comment)
    commit(db)
    return {**snapshot(comment), "actor": user.full_name}


@router.get(
    "/interactions/{iid}/attachments",
    tags=["Файлы"],
    summary="Метаданные вложений по этапам",
    response_model=list[s.AttachmentOut],
)
def attachments(iid: int, db: DB, user: User):
    require_interaction(db, user, iid)
    return db.scalars(select(Attachment).where(Attachment.interaction_id == iid)).all()


@router.post(
    "/interactions/{iid}/attachments",
    tags=["Файлы"],
    summary="Безопасная загрузка файла в этап",
    response_model=s.AttachmentOut,
    status_code=201,
    description="Multipart stage_id + file. Расширение, MIME, сигнатура и MAX_UPLOAD_MB проверяются. Хранилище вне БД, случайное имя, закрытое скачивание.",
)
async def attachment_create(
    iid: int,
    db: DB,
    user: User,
    stage_id: int = Form(...),
    file: UploadFile = File(...),
):
    item = require_interaction(db, user, iid)
    stage_belongs(db, item, stage_id)
    content = await file.read(settings.upload_limit + 1)
    filename = (file.filename or "").replace("\\", "/").split("/")[-1][:240]
    ext, mime = validate_file(content, filename, file.content_type or "")
    key = storage.save(content, ext)
    try:
        obj = Attachment(
            interaction_id=iid,
            stage_id=stage_id,
            original_filename=filename,
            stored_filename=key,
            mime_type=mime,
            size=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            uploaded_by=user.id,
        )
        db.add(obj)
        db.flush()
        audit(db, user, "attachment.upload", obj)
        commit(db)
    except Exception:
        storage.delete(key)
        raise
    return obj


@router.get(
    "/attachments/{aid}/download",
    tags=["Файлы"],
    summary="Скачать вложение с повторной проверкой доступа",
    response_class=FileResponse,
    responses={
        200: {
            "content": {
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"}
                }
            }
        }
    },
)
def attachment_download(aid: int, db: DB, user: User):
    obj = db.get(Attachment, aid)
    if not obj:
        fail(404, "NOT_FOUND", "Файл не найден")
    require_interaction(db, user, obj.interaction_id)
    audit(db, user, "attachment.download", obj)
    db.commit()
    path = storage.path(obj.stored_filename)
    if not path.exists():
        fail(404, "FILE_MISSING", "Файл отсутствует в хранилище")
    return FileResponse(
        path, filename=obj.original_filename, media_type="application/octet-stream"
    )


@router.get(
    "/dashboard",
    tags=["Аналитика"],
    summary="Пять графиков и агрегаты по текущей выборке",
    response_model=s.DashboardOut,
)
def dashboard_get(db: DB, user: User, f: Annotated[s.Filters, Depends()]):
    return dashboard(db, user, f)


@router.get(
    "/dashboard/chart/{fmt}",
    tags=["Аналитика"],
    summary="Выгрузить график востребованности программ PNG/PDF",
    response_class=Response,
    responses={
        200: {
            "content": {
                m: {"schema": {"type": "string", "format": "binary"}}
                for m in ["image/png", "application/pdf"]
            }
        }
    },
)
def dashboard_chart(fmt: str, db: DB, user: User, f: Annotated[s.Filters, Depends()]):
    if fmt not in ("png", "pdf"):
        fail(422, "FORMAT_INVALID", "Выберите PNG или PDF")
    return Response(
        chart(dashboard(db, user, f)["ranking"], fmt),
        media_type=MIMES[fmt],
        headers={"Content-Disposition": f'attachment; filename="programs.{fmt}"'},
    )


@router.post(
    "/reports/preview",
    tags=["Отчёты"],
    summary="Первые 10 строк отчёта и общее число записей",
    response_model=s.ReportPreview,
)
def report_preview(p: s.ReportInput, db: DB, user: User):
    rows, total = selected_rows(db, user, p, True)
    return {
        "columns": {c: COLUMNS[c] for c in p.columns},
        "items": [{c: r.get(c) for c in p.columns} for r in rows],
        "total": total,
    }


@router.post(
    "/reports/export",
    tags=["Отчёты"],
    summary="Отчёт XLSX/XLS/PDF/JSON по выбранным колонкам",
    response_class=Response,
    responses={
        200: {
            "content": {
                m: {"schema": {"type": "string", "format": "binary"}}
                for m in MIMES.values()
            }
        }
    },
    description="Общие фильтры и права. Не более 50 000 строк. PDF содержит название, период, дату генерации, применённые фильтры и таблицу. Excel-формулы экранируются.",
)
def report_export(p: s.ReportInput, db: DB, user: User):
    rows, _ = selected_rows(db, user, p)
    data = export(rows, p)
    db.add(
        AuditLog(
            user_id=user.id,
            action="report.export",
            entity_type="reports",
            entity_id=p.format,
            new_value={"rows": len(rows), "columns": p.columns},
        )
    )
    db.commit()
    return Response(
        data,
        media_type=MIMES[p.format],
        headers={"Content-Disposition": f'attachment; filename="report.{p.format}"'},
    )


@router.get(
    "/import/template",
    tags=["Импорт"],
    summary="Шаблон Excel с полями оригинального ТЗ",
    response_class=Response,
    responses={
        200: {
            "content": {
                MIMES["xlsx"]: {"schema": {"type": "string", "format": "binary"}}
            }
        }
    },
)
def import_template(user: User):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(list(IMPORT_FIELDS.values()))
    ws.append(
        [
            "Университет ИТМО",
            "Ростелеком",
            "РТК Облако",
            "IMPORT-001",
            "Да",
            2027,
            "В работе",
            user.full_name,
            "Учебный отдел",
            "Демонстрационный импорт",
            "Разработка",
            "Основы Python",
            100,
            60,
            2,
        ]
    )
    out = BytesIO()
    wb.save(out)
    return Response(
        out.getvalue(),
        media_type=MIMES["xlsx"],
        headers={"Content-Disposition": 'attachment; filename="import-template.xlsx"'},
    )


@router.post(
    "/import/preview",
    tags=["Импорт"],
    summary="Анализ колонок и предпросмотр XLS/XLSX",
    response_model=s.ImportPreview,
)
async def import_preview(user: Manager, file: UploadFile = File(...)):
    headers, rows = read_excel(
        await file.read(settings.upload_limit + 1),
        file.filename or "",
        file.content_type or "",
    )
    return {"headers": headers, "rows": rows[:5], "total": len(rows)}


@router.post(
    "/import/commit",
    tags=["Импорт"],
    summary="Импорт с маппингом и отчётом по каждой ошибке",
    response_model=s.OperationResult,
    description="file, mapping (JSON: поле CRM → колонка Excel), workflow_id, default_program_id. Обязательны university и product, программа задаётся маппингом или default_program_id. Каждая строка — отдельный savepoint. Ошибки не скрываются.",
)
async def import_commit(
    db: DB,
    user: Manager,
    file: UploadFile = File(...),
    mapping: str = Form(...),
    workflow_id: int = Form(1),
    default_program_id: int | None = Form(None),
):
    headers, rows = read_excel(
        await file.read(settings.upload_limit + 1),
        file.filename or "",
        file.content_type or "",
    )
    try:
        fields = json.loads(mapping)
    except ValueError:
        fail(422, "MAPPING_INVALID", "Маппинг должен быть JSON-объектом")
    if not isinstance(fields, dict) or any(
        k not in IMPORT_FIELDS or (v and v not in headers) for k, v in fields.items()
    ):
        fail(422, "MAPPING_INVALID", "Маппинг содержит неизвестные поля")
    if not fields.get("university") or not fields.get("product"):
        fail(422, "MAPPING_REQUIRED", "Сопоставьте вуз и продукт")
    result = import_rows(
        db,
        user,
        [{k: r.get(v) for k, v in fields.items() if v} for r in rows],
        workflow_id,
        default_program_id,
    )
    db.add(
        AuditLog(
            user_id=user.id,
            action="import.complete",
            entity_type="imports",
            entity_id="excel",
            new_value=result,
        )
    )
    db.commit()
    return result


@router.get(
    "/integrations",
    tags=["Интеграции"],
    summary="Режим адаптеров и последний результат синхронизации",
    response_model=dict[str, dict],
)
def integration_status(db: DB, user: User):
    return {
        source: {
            "mode": settings.integration_mode,
            "last": (
                db.get(AppSetting, "sync." + source).value
                if db.get(AppSetting, "sync." + source)
                else None
            ),
        }
        for source in ["lms", "website"]
    }


@router.get(
    "/integrations/{source}/mock-data",
    tags=["Интеграции"],
    summary="Детерминированный тестовый контракт JSON",
    response_model=list[dict],
)
def mock_data(source: str, user: User):
    if settings.integration_mode != "mock":
        fail(404, "MOCK_DISABLED", "Mock-контур отключён")
    return get_client(source).fetch_records()


@router.post(
    "/integrations/{source}/sync",
    tags=["Интеграции"],
    summary="Синхронизировать LMS или Website",
    response_model=s.OperationResult,
    description="source: lms/website. Клиент выбирается INTEGRATION_MODE=mock/http. Идемпотентный ключ source+external_id. Учитывается область доступа инициатора. Новый workflow можно предварительно создать и передать workflow_id.",
)
def integration_sync(source: str, db: DB, user: User, workflow_id: int = 1):
    from app.models import utcnow

    rows = get_client(source).fetch_records()
    result = import_rows(db, user, rows, workflow_id, None, source)
    key = "sync." + source
    obj = db.get(AppSetting, key)
    value = {"at": utcnow().isoformat(), "result": result}
    if obj:
        obj.value = value
    else:
        obj = AppSetting(key=key, value=value)
        db.add(obj)
    audit(db, user, "integration.sync", obj, None, value)
    db.commit()
    return result


@router.get(
    "/interactions/{iid}/advice",
    tags=["AI Assistant"],
    summary="Рекомендации без внешнего AI API",
    response_model=s.AdviceOut,
)
def advice(iid: int, db: DB, user: User):
    return {
        "provider": "rules",
        "suggestions": assistant.suggest(require_interaction(db, user, iid)),
    }


@router.get(
    "/audit",
    tags=["Администрирование"],
    summary="Аудит критичных операций: before/after и пользователь",
    response_model=s.Page[s.AuditOut],
)
def audit_list(
    db: DB,
    user: Admin,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    action: str = "",
):
    stmt = select(*AuditLog.__table__.c)
    if action:
        stmt = stmt.where(AuditLog.action.ilike("%" + action + "%"))
    return page_rows(db, stmt, page, page_size, AuditLog.id.desc())


@router.get(
    "/settings",
    tags=["Администрирование"],
    summary="Настройки организации и срок хранения",
    response_model=s.SettingsInput,
)
def get_app_settings(db: DB, user: Admin):
    obj = db.get(AppSetting, "general")
    return (
        obj.value
        if obj
        else {"organization": "ИТ Школа Ростелеком", "retention_days": 365}
    )


@router.put(
    "/settings",
    tags=["Администрирование"],
    summary="Обновить настройки платформы",
    response_model=s.SettingsInput,
    description="Регламентный срок хранения не вызывает автоматического удаления документов без согласованной политики заказчика.",
)
def set_app_settings(p: s.SettingsInput, db: DB, user: Admin):
    obj = db.get(AppSetting, "general")
    old = snapshot(obj) if obj else None
    if not obj:
        obj = AppSetting(key="general", value=p.model_dump())
        db.add(obj)
    else:
        obj.value = p.model_dump()
    audit(db, user, "settings.update", obj, old)
    commit(db)
    return obj.value
