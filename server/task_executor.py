import asyncio
import traceback
from datetime import datetime
from typing import Dict, Optional
from database import get_db
from llm_service import llm_service
import json

class TaskExecutor:
    def __init__(self):
        self.running = False
        self.tasks: Dict[str, asyncio.Task] = {}
    
    async def start(self):
        self.running = True
        await self.load_tasks()
    
    def stop(self):
        self.running = False
        for task in self.tasks.values():
            task.cancel()
        self.tasks.clear()
    
    async def load_tasks(self):
        with get_db() as db:
            rows = db.execute("SELECT * FROM loop_tasks WHERE enabled = 1").fetchall()
            for row in rows:
                self.add_task(dict(row))
    
    def add_task(self, task_data: dict):
        task_id = task_data["id"]
        if task_id in self.tasks:
            self.tasks[task_id].cancel()
        
        self.tasks[task_id] = asyncio.create_task(
            self.run_task_loop(task_data)
        )
    
    def remove_task(self, task_id: str):
        if task_id in self.tasks:
            self.tasks[task_id].cancel()
            del self.tasks[task_id]
    
    async def run_task_loop(self, task_data: dict):
        task_id = task_data["id"]
        interval = task_data.get("interval_seconds", 60)
        timeout = task_data.get("timeout_seconds", 30)
        
        while self.running:
            try:
                result = await asyncio.wait_for(
                    self.execute_task(task_data),
                    timeout=timeout
                )
                
                self.update_task_status(task_id, result)
                
                if result.get("triggered"):
                    action = result.get("action", "ignore")
                    
                    if action == "notify_continue":
                        self.create_notification(
                            task_id, task_data.get("name", ""),
                            result.get("message", "任务条件满足"), action
                        )
                    elif action == "notify_stop":
                        self.create_notification(
                            task_id, task_data.get("name", ""),
                            result.get("message", "任务条件满足"), action
                        )
                        self.disable_task(task_id)
                        break
                    elif action == "call_llm":
                        await self.handle_llm_call(task_data, result)
                
            except asyncio.TimeoutError:
                self.update_task_status(task_id, {"error": "执行超时"})
            except Exception as e:
                self.update_task_status(task_id, {"error": str(e)})
            
            await asyncio.sleep(interval)
    
    async def execute_task(self, task_data: dict) -> dict:
        script = task_data.get("script", "")
        
        namespace = {"__builtins__": __builtins__}
        exec(script, namespace)
        
        check_func = namespace.get("check")
        if not check_func:
            return {"triggered": False, "error": "脚本中未找到check函数"}
        
        context = {
            "api_base": __import__("config").LLM_API_BASE,
            "task_id": task_data.get("id")
        }
        
        result = await check_func(context)
        return result
    
    def update_task_status(self, task_id: str, result: dict):
        with get_db() as db:
            db.execute(
                "UPDATE loop_tasks SET last_run = ?, last_result = ? WHERE id = ?",
                (datetime.now().isoformat(), json.dumps(result, ensure_ascii=False), task_id)
            )
    
    def create_notification(self, task_id: str, task_name: str, message: str, action: str):
        with get_db() as db:
            db.execute(
                "INSERT INTO notifications (task_id, task_name, message, action) VALUES (?, ?, ?, ?)",
                (task_id, task_name, message, action)
            )
    
    def disable_task(self, task_id: str):
        with get_db() as db:
            db.execute("UPDATE loop_tasks SET enabled = 0 WHERE id = ?", (task_id,))
        self.remove_task(task_id)
    
    async def handle_llm_call(self, task_data: dict, result: dict):
        with get_db() as db:
            memories = db.execute("SELECT * FROM memories").fetchall()
            memory_list = [dict(m) for m in memories]
        
        messages = [
            {"role": "system", "content": f"你是一个智能助手。以下是用户的记忆信息：\n{json.dumps(memory_list, ensure_ascii=False)}"},
            {"role": "user", "content": f"任务 [{task_data.get('name')}] 检测到以下情况：\n{result.get('message')}\n\n请分析并给出建议。"}
        ]
        
        llm_response = await llm_service.chat(messages)
        
        self.create_notification(
            task_data.get("id"), task_data.get("name"),
            f"AI分析结果：\n{llm_response}", "llm_analysis"
        )

task_executor = TaskExecutor()
