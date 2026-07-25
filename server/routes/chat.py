from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, AsyncGenerator
import uuid
from database import get_db
from models import (
    ConversationCreate, ConversationResponse, ConversationUpdate,
    MessageCreate, MessageResponse
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

@router.put("/conversations/{conversation_id}")
async def update_conversation(conversation_id: str, data: ConversationUpdate):
    with get_db() as db:
        db.execute(
            "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (data.title, conversation_id)
        )
        row = db.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="会话不存在")
    return dict(row)

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

# TODO: 添加自动命名功能，根据对话内容自动生成会话标题

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
