from fastapi import APIRouter
from typing import List
from database import get_db
from models import NotificationResponse

router = APIRouter()

@router.get("/", response_model=List[NotificationResponse])
async def list_notifications(unread_only: bool = False):
    with get_db() as db:
        if unread_only:
            rows = db.execute(
                "SELECT * FROM notifications WHERE read = 0 ORDER BY created_at DESC"
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM notifications ORDER BY created_at DESC LIMIT 100"
            ).fetchall()
    return [dict(r) for r in rows]

@router.get("/unread-count")
async def get_unread_count():
    with get_db() as db:
        row = db.execute("SELECT COUNT(*) as count FROM notifications WHERE read = 0").fetchone()
    return {"count": row["count"]}

@router.put("/{notification_id}/read")
async def mark_as_read(notification_id: int):
    with get_db() as db:
        db.execute("UPDATE notifications SET read = 1 WHERE id = ?", (notification_id,))
    return {"status": "ok"}

@router.put("/read-all")
async def mark_all_as_read():
    with get_db() as db:
        db.execute("UPDATE notifications SET read = 1 WHERE read = 0")
    return {"status": "ok"}
