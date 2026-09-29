from sqlalchemy import select, func, cast, String, literal, union_all
from app.repositories.queries import interaction_query
from app.security.access import university_scope, team_ids
from app.core.cache import cache


def dashboard(db, user, filters):
    # Permission predicates participate in the cache key; roles themselves are never cached.
    # Do not query cache-key permissions when Redis is unavailable. The actual
    # data query always applies the live SQL access predicate independently.
    revision = cache.revision()
    key = None
    if revision is not None:
        scope = {"role": user.role, "user": user.id}
        if user.role != "admin":
            scope.update(
                universities=list(db.scalars(university_scope(user))),
                employees=list(db.scalars(team_ids(user))),
            )
        key = cache.key(
            "dashboard",
            {"scope": scope, "filters": filters.model_dump(mode="json")},
            revision,
        )
    cached = cache.get(key)
    if cached is not None:
        return cached
    q = interaction_query(user, filters).subquery()
    totals = db.execute(
        select(
            func.count(),
            func.count(func.distinct(q.c.university_id)),
            func.count(func.distinct(q.c.program_id)),
            func.count(func.distinct(q.c.product_id)),
            func.coalesce(func.sum(q.c.applications), 0),
            func.coalesce(func.sum(q.c.students), 0),
            func.coalesce(func.sum(q.c.streams), 0),
        ).select_from(q)
    ).one()
    result = dict(
        zip(
            [
                "interactions",
                "universities",
                "programs",
                "products",
                "applications",
                "students",
                "streams",
            ],
            totals,
        )
    )
    dimensions = [
        ("by_direction", q.c.direction),
        ("by_product", q.c.product),
        ("by_manager", q.c.responsible),
    ]
    # One round trip for three dimension aggregates, preserving DB-side grouping.
    grouped = union_all(
        *[
            select(
                literal(name).label("dimension"),
                col.label("name"),
                func.count().label("value"),
            ).group_by(col)
            for name, col in dimensions
        ]
    ).subquery()
    for name, _ in dimensions:
        result[name] = []
    for dimension, name, count in db.execute(
        select(grouped).order_by(grouped.c.value.desc(), grouped.c.name)
    ):
        result[dimension].append({"name": name, "value": count})
    result["by_status"] = [
        {"name": n, "value": c, "universities": u}
        for n, c, u in db.execute(
            select(
                q.c.stage, func.count(), func.count(func.distinct(q.c.university_id))
            ).group_by(q.c.stage)
        )
    ]
    month = func.substr(cast(q.c.created_at, String), 1, 7)
    result["dynamics"] = [
        {"name": n, "value": c}
        for n, c in db.execute(
            select(month, func.count()).group_by(month).order_by(month)
        )
    ]
    result["ranking"] = [
        dict(r)
        for r in db.execute(
            select(
                q.c.program.label("name"),
                func.sum(q.c.applications).label("applications"),
                func.sum(q.c.students).label("students"),
                func.sum(q.c.streams).label("streams"),
            )
            .group_by(q.c.program)
            .order_by(func.sum(q.c.applications).desc(), q.c.program)
        ).mappings()
    ]
    cache.set(key, result)
    return result
