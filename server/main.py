from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import asyncio
import json

from config import HOST, PORT, BASE_DIR
from routes import chat, tasks, memory, notifications
from task_executor import TaskExecutor

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
    return FileResponse(str(BASE_DIR / "static" / "index.html"))

@app.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            async for chunk in chat.stream_chat_response(conversation_id, message["content"]):
                await websocket.send_text(json.dumps({"type": "chunk", "content": chunk}))
            await websocket.send_text(json.dumps({"type": "done"}))
    except WebSocketDisconnect:
        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
