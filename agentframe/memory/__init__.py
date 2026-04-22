"""AgentFrame Memory Module

四层记忆系统:
- L0: WorkingMemory - 工作记忆 (TTL+TF-IDF)
- L1: EpisodicMemory - 情景记忆 (SQLite+Qdrant)
- L2: SemanticMemory - 语义记忆 (Neo4j+Qdrant)
- L3: PerceptualMemory - 感知记忆 (预留)

对应 SPEC 4.3
"""

from agentframe.memory.base import (
    Memory,
    MemoryConfig,
    MemoryItem,
    MemoryType,
    MemoryLevel,
    calculate_working_score,
    calculate_episodic_score,
    calculate_semantic_score,
)

from agentframe.memory.working import WorkingMemory
from agentframe.memory.episodic import EpisodicMemory
from agentframe.memory.semantic import SemanticMemory
from agentframe.memory.manager import MemoryManager

# PerceptualMemory 为预留接口，暂不导出
# from agentframe.memory.perceptual import PerceptualMemory

__all__ = [
    # Base
    "Memory",
    "MemoryConfig",
    "MemoryItem",
    "MemoryType",
    "MemoryLevel",
    "calculate_working_score",
    "calculate_episodic_score",
    "calculate_semantic_score",
    # Implementations
    "WorkingMemory",
    "EpisodicMemory",
    "SemanticMemory",
    "MemoryManager",
]
