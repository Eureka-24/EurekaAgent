"""Working Memory - 工作记忆

用于Agent执行过程中的临时信息存储。
对应 SPEC 3.8.3
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from agentframe.memory.base import Memory, MemoryConfig, MemoryItem, MemoryType


class WorkingMemory(Memory):
    """工作记忆实现
    
    特性:
    - 线程安全的字典存储
    - 支持临时变量和状态
    - 自动过期清理
    """

    def __init__(self, config: Optional[MemoryConfig] = None):
        super().__init__(config)
        self._variables: Dict[str, Any] = {}

    async def add(self, content: str, metadata: Optional[dict] = None) -> MemoryItem:
        """添加工作记忆"""
        item_id = str(uuid.uuid4())
        
        item = MemoryItem(
            id=item_id,
            content=content,
            memory_type=MemoryType.WORKING,
            timestamp=datetime.now(),
            metadata=metadata or {},
        )
        
        self._items[item_id] = item
        return item

    async def set_var(self, key: str, value: Any) -> None:
        """设置临时变量"""
        self._variables[key] = value

    async def get_var(self, key: str, default: Any = None) -> Any:
        """获取临时变量"""
        return self._variables.get(key, default)

    async def delete_var(self, key: str) -> bool:
        """删除临时变量"""
        if key in self._variables:
            del self._variables[key]
            return True
        return False

    def get_all_vars(self) -> Dict[str, Any]:
        """获取所有变量"""
        return dict(self._variables)

    async def get(self, item_id: str) -> Optional[MemoryItem]:
        """获取记忆"""
        return self._items.get(item_id)

    async def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """搜索记忆"""
        results = []
        query_lower = query.lower()
        
        for item in self._items.values():
            if query_lower in item.content.lower():
                results.append(item)
        
        return results[:limit]

    async def delete(self, item_id: str) -> bool:
        """删除记忆"""
        if item_id in self._items:
            del self._items[item_id]
            return True
        return False

    async def clear(self) -> int:
        """清空所有记忆和变量"""
        count = len(self._items)
        self._items.clear()
        self._variables.clear()
        return count

    async def add_thinking(self, thought: str, reasoning_type: str = "default") -> MemoryItem:
        """添加思考过程"""
        return await self.add(
            content=thought,
            metadata={
                "type": "thinking",
                "reasoning_type": reasoning_type,
                "timestamp": datetime.now().isoformat()
            }
        )

    async def add_tool_result(self, tool_name: str, result: str, success: bool = True) -> MemoryItem:
        """添加工具执行结果"""
        return await self.add(
            content=f"[{tool_name}] {result}",
            metadata={
                "type": "tool_result",
                "tool_name": tool_name,
                "success": success,
                "timestamp": datetime.now().isoformat()
            }
        )

    async def get_thinking_history(self, limit: int = 10) -> List[MemoryItem]:
        """获取思考历史"""
        thoughts = [
            item for item in self._items.values()
            if item.metadata.get("type") == "thinking"
        ]
        return sorted(thoughts, key=lambda x: x.timestamp, reverse=True)[:limit]

    async def get_tool_results(self, limit: int = 10) -> List[MemoryItem]:
        """获取工具执行结果"""
        results = [
            item for item in self._items.values()
            if item.metadata.get("type") == "tool_result"
        ]
        return sorted(results, key=lambda x: x.timestamp, reverse=True)[:limit]
