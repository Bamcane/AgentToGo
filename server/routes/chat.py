from fastapi import APIRouter, HTTPException
from typing import List, AsyncGenerator
import uuid
from database import get_db
from models import (
    ConversationCreate, ConversationResponse,
    MessageCreate, MessageResponse, ChatRequest
)
from llm_service import llm_service
import json

router = APIRouter()

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(data: ConversationCreate):
    conv_id = str(uuid.uuid4())
    with get_db() as db:
        db.execute(
            "INSERT INTO conversations (id, title) VALUES (?, ?)",
            (conv_id, data.title)
        )
        row = db.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
    return dict(row)

@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations():
    with get_db() as db:
        rows = db.execute("SELECT * FROM conversations ORDER BY updated_at DESC").fetchall()
    return [dict(r) for r in rows]

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    with get_db() as db:
        db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    return {"status": "ok"}

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(conversation_id: str):
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at",
            (conversation_id,)
        ).fetchall()
    return [dict(r) for r in rows]

@router.post("/conversations/{conversation_id}/messages")
async def send_message(conversation_id: str, data: MessageCreate):
    with get_db() as db:
        conv = db.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
        if not conv:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        db.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, "user", data.content)
        )
        
        db.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,)
        )
    
    return {"status": "ok"}

async def stream_chat_response(conversation_id: str, user_message: str) -> AsyncGenerator[str, None]:
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
            "content": f"你是一个智能助手。以下是用户的记忆信息，可以在对话中使用：\n{memory_context}"
        })
    
    for row in messages_rows:
        messages.append({"role": row["role"], "content": row["content"]})
    
    full_response = ""
    async for chunk in llm_service.chat_stream(messages):
        full_response += chunk
        yield chunk
    
    with get_db() as db:
        db.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, "assistant", full_response)
        )
