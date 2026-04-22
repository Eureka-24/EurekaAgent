"""Session - 会话管理

对应 PRD 5.5.1 和 SPEC 4.5
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import uuid

if TYPE_CHECKING:
    from agentframe.core.context import ConversationContext, WorkingMemory
    from agentframe.llm.base import MessageRole


class AgentState(Enum):
    """Agent状态"""
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    WAITING_TOOL = "waiting_tool"


@dataclass
class Session:
    """会话
    
    对应 PRD 验收标准 13.5.1:
    - 会话创建延迟<100ms
    - 会话ID唯一性100%
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    state: AgentState = AgentState.IDLE
    
    # 运行时属性
    context: Optional["ConversationContext"] = None
    working_memory: Optional["WorkingMemory"] = None
    
    def update_timestamp(self) -> None:
        """更新会话时间戳"""
        self.updated_at = datetime.now()
    
    @property
    def is_active(self) -> bool:
        """检查会话是否活跃"""
        return self.state in (AgentState.IDLE, AgentState.THINKING)
    
    @property
    def turn_count(self) -> int:
        """获取对话轮数"""
        if self.context:
            return sum(1 for m in self.context.messages if m.role.value == "user")
        return 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "state": self.state.value,
            "metadata": self.metadata,
            "turn_count": self.turn_count,
        }