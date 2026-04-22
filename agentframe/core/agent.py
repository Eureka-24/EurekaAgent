"""Agent - Agent主类

Agent是整个框架的核心，负责协调LLM、工具和记忆系统。
对应 PRD 5.5 和 SPEC 4.5
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Union

import structlog

from agentframe.core.context import (
    ConversationContext,
    ContextWindow,
    WorkingMemory,
)
from agentframe.core.session import AgentState, Session
from agentframe.llm.base import (
    GenerationConfig,
    LLMAdapter,
    Message,
    MessageRole,
    Response,
)
from agentframe.tools.registry import ToolRegistry, ToolCallResult

logger = structlog.get_logger()


class Agent:
    """Agent主类

    Agent是整个框架的核心，负责协调LLM、工具和记忆系统。
    
    功能：
    - 会话管理
    - 上下文维护
    - 工具调用
    - 多轮对话
    - 流式响应
    """
    
    def __init__(
        self,
        name: str = "AgentFrame",
        system_prompt: str = "You are a helpful AI assistant.",
        llm: Optional[LLMAdapter] = None,
        tools: Optional[ToolRegistry] = None,
        max_turns: int = 20,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """初始化Agent"""
        self.name = name
        self.system_prompt = system_prompt
        self.llm = llm
        self.tools = tools or ToolRegistry()
        self.max_turns = max_turns
        self.metadata = metadata or {}
        self._sessions: Dict[str, Session] = {}
        
        self._context_window = ContextWindow(
            max_messages=max_turns * 2,
            strategy="truncate"
        )
    
    @property
    def provider(self) -> str:
        """获取LLM提供商"""
        if self.llm:
            return self.llm.provider
        return "unknown"
    
    @property
    def model(self) -> str:
        """获取当前模型"""
        if self.llm:
            return self.llm.default_model
        return "unknown"
    
    def create_session(
        self,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Session:
        """创建会话

        对应 PRD 验收标准 13.5.1:
        - 创建延迟<100ms
        - 会话ID唯一性100%
        """
        start_time = time.time()
        
        session = Session(
            user_id=user_id,
            metadata=metadata or {},
        )
        session.context = ConversationContext(
            system_prompt=self.system_prompt
        )
        session.working_memory = WorkingMemory()
        
        self._sessions[session.id] = session
        
        elapsed = (time.time() - start_time) * 1000
        logger.info("session_created", 
                    session_id=session.id, 
                    user_id=user_id,
                    latency_ms=elapsed)
        
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self._sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info("session_deleted", session_id=session_id)
            return True
        return False
    
    def list_sessions(self, user_id: Optional[str] = None) -> List[Session]:
        """列出会话"""
        if user_id:
            return [s for s in self._sessions.values() if s.user_id == user_id]
        return list(self._sessions.values())
    
    async def chat(
        self,
        session_id: str,
        message: str,
        config: Optional[GenerationConfig] = None
    ) -> Response:
        """处理用户消息
        
        对应 PRD 验收标准 13.5.1:
        - 多轮对话(20轮)上下文准确率>98%
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        session.state = AgentState.THINKING
        
        try:
            session.context.add_message(
                role=MessageRole.USER,
                content=message
            )
            
            messages = session.context.get_messages()
            tools = self.tools.to_openai_tools_format() if self.tools else None
            
            if self.llm:
                config = config or GenerationConfig()
                response = await self.llm.generate(
                    messages=messages,
                    config=config,
                    tools=tools
                )
            else:
                raise RuntimeError("No LLM adapter configured")
            
            session.context.add_message(
                role=MessageRole.ASSISTANT,
                content=response.content
            )
            
            if response.tool_calls:
                session.state = AgentState.WAITING_TOOL
                tool_results = await self._execute_tools(response.tool_calls)
                
                for result in tool_results:
                    session.context.add_message(
                        role=MessageRole.TOOL,
                        content=result.content,
                        name=result.tool_name
                    )
                
                session.state = AgentState.THINKING
                messages = session.context.get_messages()
                response = await self.llm.generate(
                    messages=messages,
                    config=config
                )
                
                session.context.add_message(
                    role=MessageRole.ASSISTANT,
                    content=response.content
                )
            
            session.state = AgentState.IDLE
            session.update_timestamp()
            
            return response
            
        except Exception as e:
            session.state = AgentState.IDLE
            logger.error("chat_error", session_id=session_id, error=str(e))
            raise
    
    async def stream(
        self,
        session_id: str,
        message: str,
        config: Optional[GenerationConfig] = None
    ):
        """流式处理用户消息"""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        session.state = AgentState.THINKING
        
        try:
            session.context.add_message(
                role=MessageRole.USER,
                content=message
            )
            
            messages = session.context.get_messages()
            tools = self.tools.to_openai_tools_format() if self.tools else None
            
            if self.llm:
                config = config or GenerationConfig()
                async for chunk in self.llm.stream(
                    messages=messages,
                    config=config,
                    tools=tools
                ):
                    yield chunk
            else:
                raise RuntimeError("No LLM adapter configured")
            
            session.state = AgentState.IDLE
            session.update_timestamp()
            
        except Exception as e:
            session.state = AgentState.IDLE
            logger.error("stream_error", session_id=session_id, error=str(e))
            raise
    
    async def _execute_tools(
        self,
        tool_calls: List[Any]
    ) -> List[ToolCallResult]:
        """执行工具调用
        
        对应 PRD 验收标准 13.2.2:
        - 工具异常不中断 Agent
        """
        import json
        
        results = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.name
            tool_args = json.loads(tool_call.arguments) if isinstance(tool_call.arguments, str) else tool_call.arguments
            
            logger.info("tool_executing", 
                       tool_name=tool_name,
                       tool_call_id=tool_call.id)
            
            result = await self.tools.execute(
                name=tool_name,
                arguments=tool_args,
                tool_call_id=tool_call.id
            )
            
            results.append(result)
            
            logger.info("tool_executed",
                       tool_name=tool_name,
                       is_error=result.is_error,
                       execution_time=result.execution_time)
        
        return results
    
    def reset_session(self, session_id: str) -> bool:
        """重置会话上下文"""
        session = self.get_session(session_id)
        if session:
            session.context.clear()
            session.working_memory.clear()
            session.state = AgentState.IDLE
            logger.info("session_reset", session_id=session_id)
            return True
        return False
    
    def set_llm(self, llm: LLMAdapter) -> None:
        """设置LLM适配器"""
        self.llm = llm
        logger.info("llm_configured", provider=llm.provider, model=llm.default_model)
    
    def add_tool(self, name: str, handler: callable, description: str = "") -> None:
        """添加工具"""
        from agentframe.tools.registry import register_tool
        register_tool(name=name, description=description, handler=handler)
        logger.info("tool_added", tool_name=name)