import json
from database import get_db
import uuid

class ToolExecutor:
    def __init__(self):
        self.tools = {
            "save_memory": self.save_memory,
            "delete_memory": self.delete_memory,
            "create_loop_task": self.create_loop_task,
            "stop_loop_task": self.stop_loop_task,
            "list_memories": self.list_memories,
            "list_tasks": self.list_tasks
        }
    
    async def execute(self, tool_name: str, arguments: dict) -> dict:
        if tool_name not in self.tools:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        
        try:
            result = await self.tools[tool_name](**arguments)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def save_memory(self, key: str, value: str, category: str = "general") -> dict:
        with get_db() as db:
            existing = db.execute("SELECT id FROM memories WHERE key = ?", (key,)).fetchone()
            if existing:
                db.execute(
                    "UPDATE memories SET value = ?, category = ?, updated_at = CURRENT_TIMESTAMP WHERE key = ?",
                    (value, category, key)
                )
            else:
                db.execute(
                    "INSERT INTO memories (key, value, category) VALUES (?, ?, ?)",
                    (key, value, category)
                )
        return {"message": f"已保存记忆: {key}", "key": key}
    
    async def delete_memory(self, key: str) -> dict:
        with get_db() as db:
            db.execute("DELETE FROM memories WHERE key = ?", (key,))
        return {"message": f"已删除记忆: {key}", "key": key}
    
    async def create_loop_task(self, name: str, script: str, user_requirement: str = "",
                                description: str = "", interval_seconds: int = 60, 
                                timeout_seconds: int = 30) -> dict:
        task_id = str(uuid.uuid4())
        with get_db() as db:
            db.execute(
                """INSERT INTO loop_tasks (id, name, description, script, user_requirement, interval_seconds, timeout_seconds) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (task_id, name, description, script, user_requirement, interval_seconds, timeout_seconds)
            )
        return {"message": f"已创建任务: {name}", "task_id": task_id}
    
    async def stop_loop_task(self, task_id: str) -> dict:
        with get_db() as db:
            db.execute("UPDATE loop_tasks SET enabled = 0 WHERE id = ?", (task_id,))
        return {"message": f"已停止任务: {task_id}", "task_id": task_id}
    
    async def list_memories(self) -> dict:
        with get_db() as db:
            rows = db.execute("SELECT key, value, category FROM memories ORDER BY updated_at DESC").fetchall()
        return {"memories": [dict(r) for r in rows]}
    
    async def list_tasks(self) -> dict:
        with get_db() as db:
            rows = db.execute("SELECT id, name, description, enabled, last_run FROM loop_tasks ORDER BY created_at DESC").fetchall()
        return {"tasks": [dict(r) for r in rows]}

tool_executor = ToolExecutor()
