from fastapi import APIRouter, HTTPException
from typing import List
from database import get_db
from models import MemoryCreate, MemoryUpdate, MemoryResponse

router = APIRouter()

@router.get("/", response_model=List[MemoryResponse])
async def list_memories(category: str = None):
    with get_db() as db:
        if category:
            rows = db.execute(
                "SELECT * FROM memories WHERE category = ? ORDER BY updated_at DESC",
                (category,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM memories ORDER BY updated_at DESC").fetchall()
    return [dict(r) for r in rows]

@router.post("/", response_model=MemoryResponse)
async def create_memory(data: MemoryCreate):
    with get_db() as db:
        existing = db.execute("SELECT id FROM memories WHERE key = ?", (data.key,)).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="该key已存在")
        
        db.execute(
            "INSERT INTO memories (key, value, category) VALUES (?, ?, ?)",
            (data.key, data.value, data.category)
        )
        row = db.execute("SELECT * FROM memories WHERE key = ?", (data.key,)).fetchone()
    return dict(row)

@router.put("/{memory_id}", response_model=MemoryResponse)
async def update_memory(memory_id: int, data: MemoryUpdate):
    with get_db() as db:
        memory = db.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        if not memory:
            raise HTTPException(status_code=404, detail="记忆不存在")
        
        updates = ["value = ?", "updated_at = CURRENT_TIMESTAMP"]
        params = [data.value]
        
        if data.category is not None:
            updates.append("category = ?")
            params.append(data.category)
        
        params.append(memory_id)
        db.execute(
            f"UPDATE memories SET {', '.join(updates)} WHERE id = ?",
            params
        )
        row = db.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
    return dict(row)

@router.delete("/{memory_id}")
async def delete_memory(memory_id: int):
    with get_db() as db:
        db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    return {"status": "ok"}
