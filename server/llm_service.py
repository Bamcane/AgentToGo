import httpx
import json
from typing import AsyncGenerator, List, Dict, Optional
from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "保存一条记忆到记忆中。当你认为某些信息对用户很重要，值得长期保存时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "记忆的键名，例如: user_name, home_ip, nas_path"},
                    "value": {"type": "string", "description": "记忆的内容"},
                    "category": {"type": "string", "description": "分类，例如: personal, network, hardware", "default": "general"}
                },
                "required": ["key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_memory",
            "description": "删除一条记忆。当某条记忆不再有用时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "要删除的记忆键名"}
                },
                "required": ["key"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_loop_task",
            "description": "创建一个循环执行的任务。当用户要求你定期检查某些事项时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "任务名称"},
                    "description": {"type": "string", "description": "任务说明"},
                    "script": {"type": "string", "description": "Python脚本，必须包含 async def check(context: dict) -> dict 函数，返回 {'triggered': bool, 'message': str}"},
                    "user_requirement": {"type": "string", "description": "用户的要求，例如：提醒我、通知我等"},
                    "interval_seconds": {"type": "integer", "description": "执行间隔秒数", "default": 60},
                    "timeout_seconds": {"type": "integer", "description": "执行超时秒数", "default": 30}
                },
                "required": ["name", "script", "user_requirement"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "stop_loop_task",
            "description": "停止一个正在运行的循环任务。",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "任务ID"}
                },
                "required": ["task_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_memories",
            "description": "列出所有记忆。当需要查看用户已保存的信息时使用。",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "列出所有循环任务。",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]

class LLMService:
    def __init__(self):
        self.api_base = LLM_API_BASE
        self.api_key = LLM_API_KEY
        self.model = LLM_MODEL
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        response = await self.client.post(
            f"{self.api_base}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "stream": False
            }
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    
    async def chat_with_tools(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> Dict:
        response = await self.client.post(
            f"{self.api_base}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "tools": TOOLS,
                "tool_choice": "auto",
                "stream": False
            }
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]
    
    async def chat_stream(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> AsyncGenerator[str, None]:
        async with self.client.stream(
            "POST",
            f"{self.api_base}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "stream": True
            }
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        if "choices" in chunk and len(chunk["choices"]) > 0:
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                    except:
                        pass
    
    async def generate_task_script(self, description: str, memories: List[Dict]) -> Dict:
        memory_context = "\n".join([f"- {m['key']}: {m['value']}" for m in memories[:10]])
        
        system_prompt = f"""你是一个Python脚本生成器。用户会描述一个需要循环监测的任务，你需要生成一个Python脚本来执行这个任务。

当前用户的记忆信息：
{memory_context if memory_context else "暂无"}

生成的脚本必须：
1. 定义一个 async def check(context: dict) -> dict 函数
2. context 包含: api_base (LLM API地址), task_id (任务ID)
3. 返回一个字典，包含:
   - "triggered": bool - 条件是否成立
   - "message": str - 描述发生了什么（如果triggered为True）
   - "action": str - "ignore"（忽略继续）/ "notify_continue"（通知并继续）/ "notify_stop"（通知并停止）
4. 脚本只能使用标准库和requests、aiohttp库
5. 脚本要有详细的注释说明每个判断条件

请直接返回JSON格式：
{{"script": "生成的Python脚本", "description": "任务说明", "interval_seconds": 建议的执行间隔, "timeout_seconds": 建议的超时时间}}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请为以下任务生成循环监测脚本：\n{description}"}
        ]
        
        response = await self.chat(messages, temperature=0.3)
        
        import json
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(response[start:end])
        except:
            pass
        
        return {
            "script": f"async def check(context):\n    # 原始请求: {description}\n    return {{'triggered': False, 'message': '', 'action': 'ignore'}}",
            "description": description,
            "interval_seconds": 60,
            "timeout_seconds": 30
        }
    
    async def close(self):
        await self.client.aclose()

llm_service = LLMService()
