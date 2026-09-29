"""Deterministic demo fixtures. Schema creation is exclusively Alembic's responsibility."""

from datetime import datetime, timezone, date
from sqlalchemy import select, text
from app.db.session import SessionLocal
from app.core.config import settings
from app.models import (
    Employee,
    University,
    UniversityAssignment,
    UniversityContact,
    ITDirection,
    ITProgram,
    ITProduct,
    Workflow,
    WorkflowStage,
    Interaction,
    WorkflowTransition,
    AppSetting,
)

STAGES = [
    "Поиск контактов ответственного в ВУЗе",
    "Коммуникация и уточнение актуальности программ по ИТ-направлениям",
    "Организация встречи с представителями ВУЗа",
    "Обмен необходимым пакетом документов",
    "Корректировка документов перед подписанием",
    "Подписание документов",
    "Передача обучающих материалов, лицензии ИТ-продукта и документации",
    "Сопровождение внедрения ИТ-продуктов",
    "Обучение преподавателей",
    "Актуализация учебной программы",
    "Ведение занятий",
    "Актуализация документации по продукту и обучающим материалам",
    "Повышение квалификации преподавателей",
    "Контроль исполнения",
]
ACCOUNTS = [
    ("admin", "Анна Смирнова", "admin"),
    ("manager", "Михаил Волков", "manager"),
    ("user", "Елена Соколова", "user"),
    ("user2", "Александр Орлов", "user"),
    ("user3", "Мария Кузнецова", "user"),
    ("user4", "Дмитрий Морозов", "user"),
    ("user5", "Ольга Новикова", "user"),
]


def seed():
    if not settings.seed_demo:
        return
    with SessionLocal() as db:
        if db.scalar(select(Employee.id).limit(1)):
            return
        for i, (username, name, role) in enumerate(ACCOUNTS, 1):
            db.add(
                Employee(
                    id=i,
                    keycloak_user_id=f"00000000-0000-4000-8000-{i:012}",
                    full_name=name,
                    email=username + "@demo.it-school.local",
                    role=role,
                    manager_id=2 if i > 2 else None,
                )
            )
        db.flush()
        universities = [
            ("Университет ИТМО", "ИТМО", "Санкт-Петербург", "Санкт-Петербург"),
            (
                "Национальный исследовательский университет Высшая школа экономики",
                "НИУ ВШЭ",
                "Москва",
                "Москва",
            ),
            (
                "Московский физико-технический институт",
                "МФТИ",
                "Долгопрудный",
                "Московская область",
            ),
            ("Казанский федеральный университет", "КФУ", "Казань", "Татарстан"),
            (
                "Уральский федеральный университет",
                "УрФУ",
                "Екатеринбург",
                "Свердловская область",
            ),
            (
                "Новосибирский государственный университет",
                "НГУ",
                "Новосибирск",
                "Новосибирская область",
            ),
            (
                "Санкт-Петербургский политехнический университет Петра Великого",
                "СПбПУ",
                "Санкт-Петербург",
                "Санкт-Петербург",
            ),
            ("Томский государственный университет", "ТГУ", "Томск", "Томская область"),
            (
                "Южный федеральный университет",
                "ЮФУ",
                "Ростов-на-Дону",
                "Ростовская область",
            ),
            (
                "Дальневосточный федеральный университет",
                "ДВФУ",
                "Владивосток",
                "Приморский край",
            ),
            (
                "Пермский государственный национальный исследовательский университет",
                "ПГНИУ",
                "Пермь",
                "Пермский край",
            ),
            (
                "Воронежский государственный университет",
                "ВГУ",
                "Воронеж",
                "Воронежская область",
            ),
            (
                "Самарский национальный исследовательский университет",
                "Самарский университет",
                "Самара",
                "Самарская область",
            ),
            (
                "Белгородский государственный национальный исследовательский университет",
                "НИУ БелГУ",
                "Белгород",
                "Белгородская область",
            ),
            (
                "Нижегородский государственный университет имени Н. И. Лобачевского",
                "ННГУ",
                "Нижний Новгород",
                "Нижегородская область",
            ),
        ]
        for i, (name, short, city, region) in enumerate(universities, 1):
            db.add(
                University(id=i, name=name, short_name=short, city=city, region=region)
            )
            db.flush()
            db.add(UniversityAssignment(university_id=i, employee_id=3 + (i - 1) % 5))
            db.add(
                UniversityContact(
                    university_id=i,
                    full_name="Демонстрационный координатор " + short,
                    position="Координатор ИТ-программ",
                    email=f"coordinator{i}@example.org",
                    phone="+7 (000) 000-00-00",
                )
            )
        directions = [
            "Разработка",
            "Аналитика данных",
            "Кибербезопасность",
            "DevOps",
            "Тестирование",
        ]
        for i, name in enumerate(directions, 1):
            db.add(
                ITDirection(
                    id=i, name=name, description="Образовательное ИТ-направление"
                )
            )
        db.flush()
        programs = [
            "Основы Python",
            "Веб-разработка на JavaScript",
            "Аналитика данных",
            "Машинное обучение",
            "Защита цифровых систем",
            "Прикладная криптография",
            "Облачная инфраструктура",
            "Практики DevOps",
            "Ручное тестирование",
            "Автоматизация тестирования",
        ]
        for i, name in enumerate(programs, 1):
            db.add(
                ITProgram(
                    id=i,
                    name=name,
                    direction_id=(i - 1) // 2 + 1,
                    description="Учебная программа. Демонстрационные данные.",
                )
            )
        for i, (name, vendor) in enumerate(
            [
                ("Базис.WorkPlace", "Базис"),
                ("РТК Облако", "Ростелеком"),
                ("Solar Dozor", "Солар"),
                ("Postgres Pro", "Postgres Professional"),
                ("РЕД ОС", "РЕД СОФТ"),
                ("Astra Linux", "Группа Астра"),
                ("МойОфис", "Новые облачные технологии"),
                ("VK WorkSpace", "VK"),
            ],
            1,
        ):
            db.add(
                ITProduct(
                    id=i,
                    name=name,
                    vendor=vendor,
                    description="Демонстрационная запись продукта",
                )
            )
        wf = Workflow(
            id=1,
            name="Партнёрство с учебным заведением",
            description="Базовый процесс из 14 этапов оригинального ТЗ",
        )
        db.add(wf)
        db.flush()
        for i, name in enumerate(STAGES, 1):
            db.add(
                WorkflowStage(
                    id=i, workflow_id=1, name=name, order_index=i - 1, optional=i == 5
                )
            )
        db.flush()
        for i in range(45):
            item = Interaction(
                university_id=i % 15 + 1,
                program_id=i % 10 + 1,
                product_id=i % 8 + 1,
                responsible_employee_id=3 + (i % 15) % 5,
                workflow_id=1,
                current_workflow_stage_id=i % 14 + 1,
                contract_number=f"РТК-2026-{1000 + i}",
                license_signed=i % 14 >= 5,
                license_start_date=date(2026, 1, 1) if i % 14 >= 5 else None,
                license_end_date=date(2027, 12, 31),
                transfer_status="Передано" if i % 14 >= 6 else "В работе",
                notes="Синтетическая запись для демонстрации. Не является реальной статистикой.",
                applications=40 + (i * 17) % 160,
                students=20 + (i * 11) % 120,
                streams=1 + i % 4,
                created_at=datetime(
                    2026, i % 9 + 1, i % 20 + 1, 9, tzinfo=timezone.utc
                ),
            )
            db.add(item)
            db.flush()
            db.add(
                WorkflowTransition(
                    interaction_id=item.id,
                    to_stage_id=item.current_workflow_stage_id,
                    changed_by=1,
                    comment="Начальные демонстрационные данные",
                )
            )
        db.add(
            AppSetting(
                key="general",
                value={"organization": "ИТ Школа Ростелеком", "retention_days": 365},
            )
        )
        db.flush()
        if db.bind.dialect.name == "postgresql":
            for model in (
                Employee,
                University,
                ITDirection,
                ITProgram,
                ITProduct,
                Workflow,
                WorkflowStage,
            ):
                table = model.__tablename__
                db.execute(
                    text(
                        f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), (SELECT MAX(id) FROM {table}))"
                    )
                )
        db.commit()


if __name__ == "__main__":
    seed()
