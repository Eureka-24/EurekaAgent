"""Context - 上下文管理

实现对话上下文、消息历史和上下文窗口管理。
对应 PRD 5.5.1 和 SPEC 4.5
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from agentframe.llm.base import Message, MessageRole


class MessageType(Enum):
    """消息类型"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class ContextMessage:
    """上下文消息
    
    扩展的Message类，包含额外元数据
    """
    role: MessageRole
    content: str
    name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_message(self) -> Message:
        """转换为标准Message"""
        return Message(
            role=self.role,
            content=self.content,
            name=self.name
        )


@dataclass 
class ConversationContext:
    """对话上下文
    
    管理单个会话的完整上下文
    """
    messages: List[ContextMessage] = field(default_factory=list)
    system_prompt: str = ""
    max_tokens: int = 128000  # 上下文窗口大小
    
    def add_message(
        self,
        role: MessageRole,
        content: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """添加消息"""
        msg = ContextMessage(
            role=role,
            content=content,
            name=name,
            metadata=metadata or {}
        )
        self.messages.append(msg)
    
    def get_messages(self, include_system: bool = True) -> List[Message]:
        """获取消息列表"""
        if include_system and self.system_prompt:
            has_system = any(m.role == MessageRole.SYSTEM for m in self.messages)
            if not has_system:
                return [Message(role=MessageRole.SYSTEM, content=self.system_prompt)] + \
                       [m.to_message() for m in self.messages]
        
        return [m.to_message() for m in self.messages]
    
    def get_last_n_messages(self, n: int) -> List[Message]:
        """获取最近n条消息"""
        return [m.to_message() for m in self.messages[-n:]]
    
    def clear(self) -> None:
        """清空消息历史"""
        self.messages.clear()
    
    def __len__(self) -> int:
        """获取消息数量"""
        return len(self.messages)


class ContextWindow:
    """上下文窗口
    
    管理上下文大小，支持自动截断和摘要
    """
    
    def __init__(
        self,
        max_messages: int = 100,
        max_tokens: int = 128000,
        strategy: str = "truncate"
    ):
        """初始化上下文窗口"""
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self.strategy = strategy
    
    def fit(
        self,
        context: ConversationContext,
        token_count_func: Optional[callable] = None
    ) -> ConversationContext:
        """调整上下文大小"""
        if self.strategy == "truncate":
            return self._truncate(context, token_count_func)
        elif self.strategy == "summarize":
            return self._summarize(context)
        else:
            return context
    
    def _truncate(
        self,
        context: ConversationContext,
        token_count_func: Optional[callable] = None
    ) -> ConversationContext:
        """截断过长的上下文"""
        new_context = ConversationContext(
            system_prompt=context.system_prompt,
            max_tokens=self.max_tokens
        )
        
        system_messages = [m for m in context.messages if m.role == MessageRole.SYSTEM]
        other_messages = [m for m in context.messages if m.role != MessageRole.SYSTEM]
        
        for msg in reversed(other_messages):
            if len(new_context.messages) + len(system_messages) >= self.max_messages:
                break
            new_context.messages.insert(0, msg)
        
        new_context.messages = system_messages + new_context.messages
        
        return new_context
    
    def _summarize(self, context: ConversationContext) -> ConversationContext:
        """摘要过长的上下文"""
        return self._truncate(context, None)


@dataclass
class WorkingMemory:
    """工作记忆
    
    存储Agent在当前任务中的临时信息
    """
    task: Optional[str] = None
    plan: List[str] = field(default_factory=list)
    observations: List[str] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)
    
    def add_observation(self, observation: str) -> None:
        """添加观察"""
        self.observations.append(observation)
    
    def add_plan_step(self, step: str) -> None:
        """添加计划步骤"""
        self.plan.append(step)
    
    def complete_plan_step(self) -> Optional[str]:
        """完成当前计划步骤"""
        if self.plan:
            return self.plan.pop(0)
        return None
    
    def store_result(self, key: str, value: Any) -> None:
        """存储结果"""
        self.results[key] = value
    
    def get_result(self, key: str) -> Optional[Any]:
        """获取结果"""
        return self.results.get(key)
    
    def clear(self) -> None:
        """清空工作记忆"""
        self.task = None
        self.plan.clear()
        self.observations.clear()
        self.results.clear()