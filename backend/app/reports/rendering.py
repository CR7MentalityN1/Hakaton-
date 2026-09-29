from io import BytesIO
from pathlib import Path
from datetime import datetime, timezone
from xml.sax.saxutils import escape
import json
import threading
import openpyxl
import xlwt
import matplotlib

matplotlib.use("Agg")
from matplotlib.figure import Figure
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, func
from app.repositories.queries import interaction_query
from app.core.errors import fail

FONT_PATH = str(Path(matplotlib.__file__).parent / "mpl-data/fonts/ttf/DejaVuSans.ttf")
pdfmetrics.registerFont(TTFont("CRM", FONT_PATH))
render_lock = threading.Lock()
COLUMNS = {
    "university": "ВУЗ",
    "direction": "ИТ-направление",
    "program": "ИТ-программа",
    "product": "ИТ-продукт",
    "vendor": "Вендор",
    "stage": "Статус работы",
    "responsible": "Ответственный",
    "contract_number": "Номер договора",
    "license_signed": "Лицензия подписана",
    "license_start_date": "Начало лицензии",
    "license_end_date": "Срок лицензии",
    "transfer_status": "Статус передачи",
    "applications": "Заявки",
    "students": "Обучающиеся",
    "streams": "Потоки",
    "notes": "Комментарий",
    "created_at": "Создано",
}
MIMES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "pdf": "application/pdf",
    "json": "application/json",
    "png": "image/png",
}


def selected_rows(db, user, p, preview=False):
    if len(set(p.columns)) != len(p.columns) or any(
        c not in COLUMNS for c in p.columns
    ):
        fail(422, "REPORT_COLUMNS", "Выберите допустимые уникальные колонки")
    query = interaction_query(user, p)
    count = db.scalar(select(func.count()).select_from(query.subquery()))
    if count > 50000 and not preview:
        fail(422, "REPORT_LIMIT", "Максимум 50 000 строк: сузьте фильтры")
    rows = [
        dict(r)
        for r in db.execute(
            query.order_by(query.selected_columns.id).limit(10 if preview else 50001)
        ).mappings()
    ]
    return rows, count


def cell(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Да" if value else "Нет"
    if isinstance(value, (int, float)):
        return value
    text = value.isoformat() if hasattr(value, "isoformat") else str(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def export(rows, p):
    output = BytesIO()
    headers = [COLUMNS[c] for c in p.columns]
    values = [[cell(r.get(c)) for c in p.columns] for r in rows]
    if p.format == "json":
        return json.dumps(
            jsonable_encoder([{c: r.get(c) for c in p.columns} for r in rows]),
            ensure_ascii=False,
            indent=2,
        ).encode()
    if p.format == "xlsx":
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Взаимодействия"
        ws.append(headers)
        for row in values:
            ws.append(row)
        for c in ws[1]:
            c.font = openpyxl.styles.Font(bold=True, color="FFFFFF")
            c.fill = openpyxl.styles.PatternFill("solid", fgColor="7028E4")
        for i in range(1, len(headers) + 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = 28
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        wb.save(output)
    elif p.format == "xls":
        wb = xlwt.Workbook()
        ws = wb.add_sheet("Взаимодействия")
        for i, row in enumerate([headers] + values):
            for j, value in enumerate(row):
                ws.write(i, j, value)
        for j in range(len(headers)):
            ws.col(j).width = 7500
        wb.save(output)
    else:
        styles = getSampleStyleSheet()
        for style in styles.byName.values():
            style.fontName = "CRM"
        styles["BodyText"].fontSize = 7
        styles["BodyText"].leading = 10
        subtitle = f"Период создания: {p.start or 'всё время'} — {p.end or 'без ограничения'}. Сформирован: {datetime.now(timezone.utc):%d.%m.%Y %H:%M} UTC."
        applied = {
            k: v
            for k, v in p.model_dump(
                mode="json", exclude={"format", "columns", "start", "end"}
            ).items()
            if v
        }
        table = Table(
            [
                [Paragraph(escape(str(v)), styles["BodyText"]) for v in row]
                for row in [headers] + values
            ],
            colWidths=[(landscape(A4)[0] - 48) / len(headers)] * len(headers),
            repeatRows=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9ddfb")),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f6f4fa")],
                    ),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        SimpleDocTemplate(
            output,
            pagesize=landscape(A4),
            leftMargin=24,
            rightMargin=24,
            topMargin=25,
            bottomMargin=25,
        ).build(
            [
                Paragraph("ИТ Школа · Отчёт по взаимодействиям", styles["Title"]),
                Paragraph(escape(subtitle), styles["Normal"]),
                Spacer(1, 7),
                Paragraph(
                    "Фильтры: "
                    + escape(
                        json.dumps(applied, ensure_ascii=False)
                        if applied
                        else "все доступные данные"
                    )
                    + f". Записей: {len(rows)}.",
                    styles["Normal"],
                ),
                Spacer(1, 15),
                table,
            ]
        )
    return output.getvalue()


def chart(ranking, fmt):
    with render_lock:
        fig = Figure(figsize=(12, 7), layout="constrained")
        ax = fig.subplots()
        names = [r["name"] for r in ranking]
        values = [r["applications"] for r in ranking]
        ax.barh(names[::-1], values[::-1], color="#7028e4")
        ax.set_xlabel("Заявки на обучение")
        ax.set_title("Востребованность ИТ-программ")
        ax.spines[["top", "right"]].set_visible(False)
        if not names:
            ax.text(0.5, 0.5, "Нет данных", ha="center", transform=ax.transAxes)
        out = BytesIO()
        fig.savefig(out, format=fmt, dpi=150)
        fig.clear()
        return out.getvalue()
