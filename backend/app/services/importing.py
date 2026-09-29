from io import BytesIO
from datetime import date, datetime
import openpyxl
import xlrd
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from pydantic import ValidationError
from app.models import (
    University,
    ITDirection,
    ITProgram,
    ITProduct,
    Employee,
    UniversityContact,
    Interaction,
)
from app.schemas.dto import InteractionInput
from app.security.access import require_university, require_interaction
from app.services import interactions
from app.services.common import audit
from app.services.storage import validate_file
from app.core.errors import fail
from app.core.cache import cache

IMPORT_FIELDS = {
    "university": "Название ВУЗа",
    "vendor": "Вендор",
    "product": "ПО",
    "contract_number": "Номер договора",
    "license_signed": "Подписание лицензии",
    "license_end_date": "Срок действия лицензии",
    "transfer_status": "Статус по передаче",
    "responsible": "ФИО Менеджера",
    "university_contact": "Ответственные от ВУЗа",
    "notes": "Комментарий",
    "direction": "ИТ-направление",
    "program": "ИТ-программа",
    "applications": "Заявки",
    "students": "Обучающиеся",
    "streams": "Потоки",
}


def read_excel(content, filename, mime):
    ext, _ = validate_file(content, filename, mime)
    if ext not in ("xls", "xlsx"):
        fail(415, "EXCEL_REQUIRED", "Выберите XLS или XLSX")
    try:
        if ext == "xlsx":
            wb = openpyxl.load_workbook(
                BytesIO(content), read_only=True, data_only=True
            )
            ws = wb.active
            if ws.max_row and ws.max_row > 10001:
                fail(422, "IMPORT_LIMIT", "Максимум 10 000 строк")
            values = list(ws.iter_rows(values_only=True))
            wb.close()
        else:
            wb = xlrd.open_workbook(file_contents=content)
            ws = wb.sheet_by_index(0)
            if ws.nrows > 10001:
                fail(422, "IMPORT_LIMIT", "Максимум 10 000 строк")
            values = [
                [
                    xlrd.xldate_as_datetime(ws.cell(i, j).value, wb.datemode)
                    .date()
                    .isoformat()
                    if ws.cell(i, j).ctype == xlrd.XL_CELL_DATE
                    else ws.cell(i, j).value
                    for j in range(ws.ncols)
                ]
                for i in range(ws.nrows)
            ]
        if not values:
            fail(422, "IMPORT_EMPTY", "Таблица пуста")
        headers = [str(v or "").strip() for v in values[0]]
        if len(set(headers)) != len(headers) or any(not h for h in headers):
            fail(422, "IMPORT_HEADERS", "Заголовки должны быть непустыми и уникальными")
        return headers, [
            dict(zip(headers, row))
            for row in values[1:]
            if any(v not in (None, "") for v in row)
        ]
    except HTTPException:
        raise
    except Exception:
        fail(422, "IMPORT_INVALID", "Не удалось прочитать Excel-файл")


def named(db, model, name, **defaults):
    name = str(name or "").strip()
    if not name or len(name) > 250:
        fail(422, "IMPORT_VALUE", "Пустое или слишком длинное название")
    obj = db.scalar(select(model).where(model.name == name))
    if obj is None:
        obj = model(name=name, **defaults)
        db.add(obj)
        db.flush()
    return obj


def ingest(db, user, row, workflow_id, default_program_id, source=None):
    name = str(row.get("university") or "").strip()
    uni = db.scalar(select(University).where(University.name == name))
    if uni is None:
        if user.role != "admin":
            fail(403, "SCOPE_FORBIDDEN", "Новый вуз может создать администратор")
        uni = named(
            db, University, name, short_name="", city="Не указан", region="Не указан"
        )
    require_university(db, user, uni.id)
    program = db.get(ITProgram, default_program_id) if default_program_id else None
    if row.get("program"):
        program = db.scalar(
            select(ITProgram).where(ITProgram.name == str(row["program"]))
        )
        if program is None:
            direction = named(
                db,
                ITDirection,
                row.get("direction") or "Не указано",
                description="Добавлено при импорте",
            )
            program = named(
                db,
                ITProgram,
                row["program"],
                direction_id=direction.id,
                description="Добавлено при импорте",
            )
    if not program:
        fail(
            422,
            "PROGRAM_REQUIRED",
            "Сопоставьте программу или выберите программу по умолчанию",
        )
    product = named(
        db,
        ITProduct,
        row.get("product"),
        vendor=str(row.get("vendor") or "Не указан"),
        description="",
    )
    if row.get("vendor"):
        product.vendor = str(row["vendor"])
    fields = {
        k: v
        for k, v in row.items()
        if k in InteractionInput.model_fields
        and k not in ("university_id", "program_id", "product_id", "workflow_id")
        and v is not None
        and v != ""
    }
    for key in ("contract_number", "transfer_status", "notes"):
        if key in fields:
            fields[key] = str(fields[key])
    if "license_signed" in fields:
        v = fields["license_signed"]
        if isinstance(v, (date, datetime)):
            fields["license_start_date"] = v.date() if isinstance(v, datetime) else v
            fields["license_signed"] = True
        elif isinstance(v, str):
            if v.lower() in ("да", "true", "1", "подписано"):
                fields["license_signed"] = True
            elif v.lower() in ("нет", "false", "0", "не подписано"):
                fields["license_signed"] = False
            else:
                fields["license_start_date"] = date.fromisoformat(v[:10])
                fields["license_signed"] = True
    for k in ("license_start_date", "license_end_date"):
        if k in fields:
            v = fields[k]
            if isinstance(v, datetime):
                fields[k] = v.date()
            elif isinstance(v, (int, float)) or (
                isinstance(v, str) and len(v) == 4 and v.isdigit()
            ):
                fields[k] = date(int(v), 12, 31)
            elif isinstance(v, str):
                fields[k] = date.fromisoformat(v[:10])
    if row.get("responsible"):
        employee = db.scalar(
            select(Employee).where(
                Employee.full_name == str(row["responsible"]), Employee.active.is_(True)
            )
        )
        if not employee:
            fail(
                422,
                "EMPLOYEE_INVALID",
                "ФИО менеджера не совпадает с активным сотрудником",
            )
        fields["responsible_employee_id"] = employee.id
    existing = None
    if source:
        external_id = str(row.get("external_id") or "")
        if not external_id or len(external_id) > 250:
            fail(422, "EXTERNAL_ID_REQUIRED", "Нужен корректный внешний идентификатор")
        existing = db.scalar(
            select(Interaction).where(
                Interaction.source == source, Interaction.external_id == external_id
            )
        )
    elif fields.get("contract_number"):
        existing = db.scalar(
            select(Interaction).where(
                Interaction.university_id == uni.id,
                Interaction.program_id == program.id,
                Interaction.product_id == product.id,
                Interaction.contract_number == str(fields["contract_number"]),
            )
        )
    if existing:
        require_interaction(db, user, existing.id)
        if existing.university_id != uni.id or existing.workflow_id != workflow_id:
            fail(
                409,
                "IDENTITY_CONFLICT",
                "Источник меняет вуз или workflow существующей записи",
            )
        values = {k: getattr(existing, k) for k in InteractionInput.model_fields}
        values.update(fields, program_id=program.id, product_id=product.id)
        p = InteractionInput(**values)
        item = existing
        if all(getattr(existing, k) == v for k, v in p.model_dump().items()):
            outcome = "skipped"
        else:
            interactions.edit(db, user, existing, p, existing.version)
            outcome = "updated"
    else:
        fields.setdefault("responsible_employee_id", user.id)
        p = InteractionInput(
            university_id=uni.id,
            program_id=program.id,
            product_id=product.id,
            workflow_id=workflow_id,
            **fields,
        )
        item = interactions.create(db, user, p)
        if source:
            item.source = source
            item.external_id = external_id
        outcome = "created"
    if row.get("university_contact"):
        name = str(row["university_contact"])[:250]
        if not db.scalar(
            select(UniversityContact.id).where(
                UniversityContact.university_id == uni.id,
                UniversityContact.full_name == name,
            )
        ):
            db.add(
                UniversityContact(
                    university_id=uni.id,
                    full_name=name,
                    position="Ответственный от вуза",
                )
            )
            if outcome == "skipped":
                outcome = "updated"
    audit(db, user, "integration." + source if source else "import.row", item)
    return outcome


def import_rows(db, user, rows, workflow_id, default_program_id, source=None):
    result = {"created": 0, "updated": 0, "skipped": 0, "errors": []}
    for index, row in enumerate(rows, 2 if not source else 1):
        try:
            # Each row is atomic; a failed row does not discard valid rows from the file.
            with db.begin_nested():
                outcome = ingest(db, user, row, workflow_id, default_program_id, source)
                db.flush()
            result[outcome] += 1
        except IntegrityError:
            result["errors"].append(
                {"row": index, "message": "Конфликт уникальности или связей данных"}
            )
            result["skipped"] += 1
        except (HTTPException, ValidationError, ValueError) as exc:
            message = (
                exc.detail.get("message", "Ошибка строки")
                if isinstance(exc, HTTPException)
                else "Некорректное значение поля: " + str(exc).splitlines()[0]
            )
            result["errors"].append({"row": index, "message": message})
            result["skipped"] += 1
    db.commit()
    cache.invalidate()
    return result
