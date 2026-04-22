"""API Routes - API路由

实现会话、工具、Agent等REST API接口。
对应 PRD 7.1.1, 7.1.2 和 SPEC 5.1.1, 5.1.2
"""

import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from agentframe.core.agent import Agent
from agentframe.llm.base import GenerationConfig
from agentframe.tools.registry import ToolRegistry


# ===========================================
# Request/Response Models
# ===========================================

class ChatRequest(BaseModel):
    """对话请求"""
    session_id: Optional[str] = Field(None, description="会话ID")
    message: str = Field(..., description="用户消息")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(4096, gt=0)


class ChatResponse(BaseModel):
    """对话响应"""
    session_id: str
    message: str
    finish_reason: str


class SessionCreateRequest(BaseModel):
    """创建会话请求"""
    user_id: str
    metadata: Optional[Dict[str, Any]] = None


class SessionResponse(BaseModel):
    """会话响应"""
    id: str
    user_id: str
    created_at: str
    state: str
    turn_count: int
    metadata: Dict[str, Any]


class ToolRegisterRequest(BaseModel):
    """注册工具请求"""
    name: str
    description: str
    parameters: Dict[str, Any]


class ToolResponse(BaseModel):
    """工具响应"""
    name: str
    description: str
    parameters: Dict[str, Any]
    category: str
    version: str


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    agents: int
    tools: int


# ===========================================
# App Factory
# ===========================================

def create_app(
    agent: Optional[Agent] = None,
    tool_registry: Optional[ToolRegistry] = None,
    title: str = "AgentFrame API",
    version: str = "1.0.0"
) -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(title=title, version=version, description="AgentFrame - 智能Agent框架 API")
    
    _agent = agent or Agent()
    _tool_registry = tool_registry or ToolRegistry()
    
    # Health Check
    @app.get("/health", response_model=HealthResponse, tags=["System"])
    async def health_check():
        return HealthResponse(
            status="healthy",
            version=version,
            agents=len(_agent.list_sessions()),
            tools=_tool_registry.tool_count
        )
    
    # Session APIs
    @app.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED, tags=["Sessions"])
    async def create_session(request: SessionCreateRequest):
        session = _agent.create_session(user_id=request.user_id, metadata=request.metadata or {})
        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            created_at=session.created_at.isoformat(),
            state=session.state.value,
            turn_count=session.turn_count,
            metadata=session.metadata
        )
    
    @app.get("/sessions", response_model=List[SessionResponse], tags=["Sessions"])
    async def list_sessions(user_id: Optional[str] = None):
        sessions = _agent.list_sessions(user_id=user_id)
        return [
            SessionResponse(
                id=s.id, user_id=s.user_id, created_at=s.created_at.isoformat(),
                state=s.state.value, turn_count=s.turn_count, metadata=s.metadata
            ) for s in sessions
        ]
    
    @app.get("/sessions/{session_id}", response_model=SessionResponse, tags=["Sessions"])
    async def get_session(session_id: str):
        session = _agent.get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session not found: {session_id}")
        return SessionResponse(
            id=session.id, user_id=session.user_id, created_at=session.created_at.isoformat(),
            state=session.state.value, turn_count=session.turn_count, metadata=session.metadata
        )
    
    @app.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Sessions"])
    async def delete_session(session_id: str):
        if not _agent.delete_session(session_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session not found: {session_id}")
    
    @app.post("/sessions/{session_id}/reset", response_model=SessionResponse, tags=["Sessions"])
    async def reset_session(session_id: str):
        if not _agent.reset_session(session_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session not found: {session_id}")
        session = _agent.get_session(session_id)
        return SessionResponse(
            id=session.id, user_id=session.user_id, created_at=session.created_at.isoformat(),
            state=session.state.value, turn_count=session.turn_count, metadata=session.metadata
        )
    
    # Chat API
    @app.post("/chat", response_model=ChatResponse, tags=["Chat"])
    async def chat(request: ChatRequest):
        if request.session_id:
            session = _agent.get_session(request.session_id)
            if not session:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session not found: {request.session_id}")
        else:
            session = _agent.create_session(user_id=f"anonymous_{uuid.uuid4().hex[:8]}", metadata={"source": "api"})
        
        config = GenerationConfig(temperature=request.temperature, max_tokens=request.max_tokens)
        
        try:
            response = await _agent.chat(session_id=session.id, message=request.message, config=config)
            return ChatResponse(session_id=session.id, message=response.content, finish_reason=response.finish_reason)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Chat error: {str(e)}")
    
    # Tool APIs
    @app.get("/tools", response_model=List[ToolResponse], tags=["Tools"])
    async def list_tools():
        tools = _tool_registry.list_tools()
        return [
            ToolResponse(
                name=t.name, description=t.description, parameters=t.parameters,
                category=t.metadata.category.value, version=t.metadata.version
            ) for t in tools
        ]
    
    @app.post("/tools", response_model=ToolResponse, status_code=status.HTTP_201_CREATED, tags=["Tools"])
    async def register_tool(request: ToolRegisterRequest):
        if _tool_registry.get_tool(request.name):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Tool already exists: {request.name}")
        
        from agentframe.tools.registry import ToolDefinition, ToolMetadata
        tool_def = ToolDefinition(
            name=request.name, description=request.description,
            parameters=request.parameters,
            handler=lambda **kwargs: f"Tool {request.name} executed",
            metadata=ToolMetadata()
        )
        _tool_registry.register_tool(tool_def)
        
        return ToolResponse(
            name=tool_def.name, description=tool_def.description, parameters=tool_def.parameters,
            category=tool_def.metadata.category.value, version=tool_def.metadata.version
        )
    
    @app.get("/tools/{tool_name}", response_model=ToolResponse, tags=["Tools"])
    async def get_tool(tool_name: str):
        tool = _tool_registry.get_tool(tool_name)
        if not tool:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tool not found: {tool_name}")
        return ToolResponse(
            name=tool.name, description=tool.description, parameters=tool.parameters,
            category=tool.metadata.category.value, version=tool.metadata.version
        )
    
    @app.delete("/tools/{tool_name}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tools"])
    async def unregister_tool(tool_name: str):
        from agentframe.tools.registry import ToolRegistry as TR
        if not await TR().unregister(tool_name):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tool not found: {tool_name}")
    
    return app
