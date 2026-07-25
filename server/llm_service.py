import httpx
from typing import AsyncGenerator, List, Dict, Optional
from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL

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
                        chunk = __import__("json").loads(data)
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
