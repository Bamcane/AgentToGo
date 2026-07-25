from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ConversationCreate(BaseModel):
    title: Optional[str] = "新会话"

class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str

class MessageCreate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: int
    conversation_id: str
    role: str
    content: str
    created_at: str

class MemoryCreate(BaseModel):
    key: str
    value: str
    category: Optional[str] = "general"

class MemoryUpdate(BaseModel):
    value: str
    category: Optional[str] = None

class MemoryResponse(BaseModel):
    id: int
    key: str
    value: str
    category: str
    created_at: str
    updated_at: str

class LoopTaskCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    script: str
    interval_seconds: int = 60
    timeout_seconds: int = 30

class LoopTaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    script: Optional[str] = None
    interval_seconds: Optional[int] = None
    timeout_seconds: Optional[int] = None
    enabled: Optional[bool] = None

class LoopTaskResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    script: str
    interval_seconds: int
    timeout_seconds: int
    enabled: bool
    last_run: Optional[str]
    last_result: Optional[str]
    created_at: str
    updated_at: str

class NotificationResponse(BaseModel):
    id: int
    task_id: Optional[str]
    task_name: Optional[str]
    message: str
    action: str
    read: bool
    created_at: str

class ChatRequest(BaseModel):
    message: str

class GenerateTaskRequest(BaseModel):
    description: str
