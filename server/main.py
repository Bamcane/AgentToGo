from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import asyncio
import json

from config import HOST, PORT, BASE_DIR
from routes import chat, tasks, memory, notifications
from task_executor import TaskExecutor
from llm_service import llm_service
from tool_executor import tool_executor
from database import get_db

task_executor = TaskExecutor()

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(task_executor.start())
    yield
    task_executor.stop()

app = FastAPI(title="AgentToGo", lifespan=lifespan)

app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(memory.router, prefix="/api/memory", tags=["memory"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

@app.get("/")
async def index():
    return FileResponse(str(BASE_DIR / "static" / "home.html"))

@app.get("/chat")
async def chat_page():
    return FileResponse(str(BASE_DIR / "static" / "chat.html"))

@app.get("/chat/{conversation_id}")
async def chat_with_id(conversation_id: str):
    return FileResponse(str(BASE_DIR / "static" / "chat.html"))

@app.get("/tasks")
async def tasks_page():
    return FileResponse(str(BASE_DIR / "static" / "tasks.html"))

@app.get("/memory")
async def memory_page():
    return FileResponse(str(BASE_DIR / "static" / "memory.html"))

async def process_chat_with_tools(conversation_id: str, user_message: str, websocket: WebSocket = None):
    """处理聊天，支持tool calls"""
    
    with get_db() as db:
        db.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, "user", user_message)
        )
        
        memories = db.execute("SELECT key, value FROM memories").fetchall()
        memory_context = "\n".join([f"- {m['key']}: {m['value']}" for m in memories])
        
        messages_rows = db.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY created_at",
            (conversation_id,)
        ).fetchall()
    
    messages = []
    if memory_context:
        messages.append({
            "role": "system",
            "content": f"""你是一个智能助手。以下是用户的记忆信息，可以在对话中使用：
{memory_context}

你可以使用以下工具：
- save_memory: 保存重要信息到记忆
- delete_memory: 删除不再需要的记忆
- create_loop_task: 创建循环任务（当用户要求定期检查某些事项时）
- stop_loop_task: 停止循环任务
- list_memories: 查看所有记忆
- list_tasks: 查看所有循环任务

当用户要求定期检查、监控、提醒等事项时，你应该创建循环任务而不是只在当前对话中回答。
创建任务时必须包含user_requirement参数，说明用户的要求（如：提醒我、通知我等）。"""
        })
    else:
        messages.append({
            "role": "system",
            "content": """你是一个智能助手。你可以使用以下工具：
- save_memory: 保存重要信息到记忆
- delete_memory: 删除不再需要的记忆
- create_loop_task: 创建循环任务（当用户要求定期检查某些事项时）
- stop_loop_task: 停止循环任务
- list_memories: 查看所有记忆
- list_tasks: 查看所有循环任务

当用户要求定期检查、监控、提醒等事项时，你应该创建循环任务而不是只在当前对话中回答。
创建任务时必须包含user_requirement参数，说明用户的要求（如：提醒我、通知我等）。"""
        })
    
    for row in messages_rows:
        messages.append({"role": row["role"], "content": row["content"]})
    
    max_iterations = 5
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        response = await llm_service.chat_with_tools(messages)
        
        if response.get("tool_calls"):
            tool_call = response["tool_calls"][0]
            tool_name = tool_call["function"]["name"]
            tool_args = json.loads(tool_call["function"]["arguments"])
            
            if websocket:
                await websocket.send_text(json.dumps({
                    "type": "tool_call",
                    "tool": tool_name,
                    "arguments": tool_args
                }))
            
            result = await tool_executor.execute(tool_name, tool_args)
            
            if websocket:
                await websocket.send_text(json.dumps({
                    "type": "tool_result",
                    "tool": tool_name,
                    "result": result
                }))
            
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [tool_call]
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(result, ensure_ascii=False)
            })
            
            continue
        
        content = response.get("content", "")
        
        with get_db() as db:
            db.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
                (conversation_id, "assistant", content)
            )
            db.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (conversation_id,)
            )
        
        return content
    
    return "（已达到最大工具调用次数）"

@app.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            user_message = message["content"]
            
            with get_db() as db:
                conv = db.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
                if not conv:
                    await websocket.send_text(json.dumps({"type": "error", "content": "会话不存在"}))
                    continue
            
            try:
                response_content = await process_chat_with_tools(conversation_id, user_message, websocket)
                
                await websocket.send_text(json.dumps({
                    "type": "chunk",
                    "content": response_content
                }))
                await websocket.send_text(json.dumps({"type": "done"}))
                
            except Exception as e:
                await websocket.send_text(json.dumps({"type": "error", "content": str(e)}))
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket错误: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
