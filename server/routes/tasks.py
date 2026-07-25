from fastapi import APIRouter, HTTPException
from typing import List
import uuid
from database import get_db
from models import LoopTaskCreate, LoopTaskUpdate, LoopTaskResponse, GenerateTaskRequest
from llm_service import llm_service
from task_executor import task_executor

router = APIRouter()

@router.get("/", response_model=List[LoopTaskResponse])
async def list_tasks():
    with get_db() as db:
        rows = db.execute("SELECT * FROM loop_tasks ORDER BY created_at DESC").fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["enabled"] = bool(d["enabled"])
        result.append(d)
    return result

@router.post("/", response_model=LoopTaskResponse)
async def create_task(data: LoopTaskCreate):
    task_id = str(uuid.uuid4())
    with get_db() as db:
        db.execute(
            """INSERT INTO loop_tasks (id, name, description, script, interval_seconds, timeout_seconds) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (task_id, data.name, data.description, data.script, data.interval_seconds, data.timeout_seconds)
        )
        row = db.execute("SELECT * FROM loop_tasks WHERE id = ?", (task_id,)).fetchone()
    
    task_executor.add_task(dict(row))
    
    d = dict(row)
    d["enabled"] = bool(d["enabled"])
    return d

@router.put("/{task_id}", response_model=LoopTaskResponse)
async def update_task(task_id: str, data: LoopTaskUpdate):
    with get_db() as db:
        task = db.execute("SELECT * FROM loop_tasks WHERE id = ?", (task_id,)).fetchone()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        updates = []
        params = []
        if data.name is not None:
            updates.append("name = ?")
            params.append(data.name)
        if data.description is not None:
            updates.append("description = ?")
            params.append(data.description)
        if data.script is not None:
            updates.append("script = ?")
            params.append(data.script)
        if data.interval_seconds is not None:
            updates.append("interval_seconds = ?")
            params.append(data.interval_seconds)
        if data.timeout_seconds is not None:
            updates.append("timeout_seconds = ?")
            params.append(data.timeout_seconds)
        if data.enabled is not None:
            updates.append("enabled = ?")
            params.append(int(data.enabled))
        
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(task_id)
            db.execute(
                f"UPDATE loop_tasks SET {', '.join(updates)} WHERE id = ?",
                params
            )
        
        row = db.execute("SELECT * FROM loop_tasks WHERE id = ?", (task_id,)).fetchone()
    
    if data.enabled is False:
        task_executor.remove_task(task_id)
    else:
        task_executor.add_task(dict(row))
    
    d = dict(row)
    d["enabled"] = bool(d["enabled"])
    return d

@router.delete("/{task_id}")
async def delete_task(task_id: str):
    with get_db() as db:
        db.execute("DELETE FROM loop_tasks WHERE id = ?", (task_id,))
    task_executor.remove_task(task_id)
    return {"status": "ok"}

@router.post("/generate")
async def generate_task(data: GenerateTaskRequest):
    with get_db() as db:
        memories = db.execute("SELECT key, value FROM memories").fetchall()
        memory_list = [dict(m) for m in memories]
    
    result = await llm_service.generate_task_script(data.description, memory_list)
    
    return {
        "name": data.description[:50],
        "description": result.get("description", ""),
        "script": result.get("script", ""),
        "interval_seconds": result.get("interval_seconds", 60),
        "timeout_seconds": result.get("timeout_seconds", 30)
    }
