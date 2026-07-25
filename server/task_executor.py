import asyncio
import traceback
import json
from datetime import datetime
from typing import Dict, Optional
from database import get_db
from llm_service import llm_service

class TaskExecutor:
    def __init__(self):
        self.running = False
        self.tasks: Dict[str, asyncio.Task] = {}
        self.check_interval = 5  # 每5秒检查一次数据库中的新任务
    
    async def start(self):
        self.running = True
        asyncio.create_task(self.watch_new_tasks())
    
    def stop(self):
        self.running = False
        for task in self.tasks.values():
            task.cancel()
        self.tasks.clear()
    
    async def watch_new_tasks(self):
        """持续监控数据库中的新任务"""
        while self.running:
            try:
                with get_db() as db:
                    rows = db.execute("SELECT * FROM loop_tasks WHERE enabled = 1").fetchall()
                    current_ids = set(self.tasks.keys())
                    db_ids = set(row["id"] for row in rows)
                    
                    # 添加新任务
                    for row in rows:
                        if row["id"] not in current_ids:
                            self.add_task(dict(row))
                    
                    # 移除已删除或禁用的任务
                    for task_id in current_ids - db_ids:
                        self.remove_task(task_id)
                        
            except Exception as e:
                print(f"监控任务错误: {e}")
            
            await asyncio.sleep(self.check_interval)
    
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
                    # 任务触发，交给LLM处理
                    await self.handle_triggered_task(task_data, result)
                
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
    
    async def handle_triggered_task(self, task_data: dict, result: dict):
        """任务触发后，交给LLM处理"""
        task_id = task_data["id"]
        task_name = task_data.get("name", "未命名任务")
        user_requirement = task_data.get("user_requirement", "")
        
        with get_db() as db:
            memories = db.execute("SELECT key, value FROM memories").fetchall()
            memory_list = [dict(m) for m in memories]
        
        memory_context = "\n".join([f"- {m['key']}: {m['value']}" for m in memory_list])
        
        prompt = f"""一个循环任务已被触发，需要你决定如何处理。

任务信息：
- 名称: {task_name}
- 用户要求: {user_requirement}
- 检测结果: {result.get('message', '无详细信息')}

当前用户记忆：
{memory_context if memory_context else "暂无"}

请决定如何处理这个情况。你可以：
1. 发送通知给用户（使用notify_user工具）
2. 删除这个任务（使用delete_task工具）
3. 两个都做

请用工具调用来执行你的决定。"""

        messages = [
            {"role": "system", "content": "你是一个智能助手。请分析任务触发情况，并通过工具调用来处理。"},
            {"role": "user", "content": prompt}
        ]
        
        # 定义处理工具
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "notify_user",
                    "description": "发送通知给用户",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string", "description": "通知内容"}
                        },
                        "required": ["message"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_task",
                    "description": "删除这个循环任务",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            }
        ]
        
        try:
            response = await llm_service.client.post(
                f"{llm_service.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {llm_service.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": llm_service.model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                message = data["choices"][0]["message"]
                
                if message.get("tool_calls"):
                    for tool_call in message["tool_calls"]:
                        tool_name = tool_call["function"]["name"]
                        tool_args = json.loads(tool_call["function"]["arguments"])
                        
                        if tool_name == "notify_user":
                            self.create_notification(task_id, task_name, tool_args.get("message", "任务提醒"))
                        elif tool_name == "delete_task":
                            self.disable_task(task_id)
                            self.create_notification(task_id, task_name, "任务已自动删除")
        except Exception as e:
            # 如果LLM处理失败，至少发送基本通知
            self.create_notification(task_id, task_name, f"任务触发: {result.get('message', '条件满足')}")
    
    def update_task_status(self, task_id: str, result: dict):
        with get_db() as db:
            db.execute(
                "UPDATE loop_tasks SET last_run = ?, last_result = ? WHERE id = ?",
                (datetime.now().isoformat(), json.dumps(result, ensure_ascii=False), task_id)
            )
    
    def create_notification(self, task_id: str, task_name: str, message: str):
        with get_db() as db:
            db.execute(
                "INSERT INTO notifications (task_id, task_name, message, action) VALUES (?, ?, ?, ?)",
                (task_id, task_name, message, "notify")
            )
    
    def disable_task(self, task_id: str):
        with get_db() as db:
            db.execute("UPDATE loop_tasks SET enabled = 0 WHERE id = ?", (task_id,))
        self.remove_task(task_id)

task_executor = TaskExecutor()
