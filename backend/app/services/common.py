from fastapi.encoders import jsonable_encoder
from app.models import AuditLog


def snapshot(obj):
    return jsonable_encoder(
        {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    )


def audit(db, user, action, obj, old=None, new=None):
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            action=action,
            entity_type=obj.__tablename__,
            entity_id=str(getattr(obj, "id", getattr(obj, "key", ""))),
            old_value=old,
            new_value=new if new is not None else snapshot(obj),
        )
    )
