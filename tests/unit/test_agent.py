"""Agent Core Tests - Agent核心测试

测试Agent和Session的功能。
对应 PRD 验收标准 13.5.1

运行: pytest tests/unit/test_agent.py -v
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentframe.core.agent import Agent
from agentframe.core.context import (
    ConversationContext,
    ContextMessage,
    ContextWindow,
    WorkingMemory,
)
from agentframe.core.session import AgentState, Session
from agentframe.llm.base import (
    GenerationConfig,
    Message,
    MessageRole,
    Response,
    ToolCall,
)
from agentframe.tools.registry import ToolRegistry


class TestSession:
    """测试会话"""

    def test_session_creation(self):
        """测试创建会话"""
        session = Session(user_id="user123")
        
        assert session.user_id == "user123"
        assert session.state == AgentState.IDLE
        assert session.id is not None
        assert len(session.id) > 0

    def test_session_id_uniqueness(self):
        """测试会话ID唯一性"""
        sessions = [Session() for _ in range(100)]
        ids = [s.id for s in sessions]
        
        assert len(ids) == len(set(ids))

    def test_session_update_timestamp(self):
        """测试更新时间戳"""
        session = Session()
        original_time = session.updated_at
        
        time.sleep(0.01)
        session.update_timestamp()
        
        assert session.updated_at >= original_time

    def test_session_is_active(self):
        """测试会话活跃状态"""
        session = Session()
        
        assert session.is_active is True
        
        session.state = AgentState.THINKING
        assert session.is_active is True
        
        session.state = AgentState.WAITING_TOOL
        assert session.is_active is False

    def test_session_turn_count(self):
        """测试对话轮数"""
        session = Session()
        session.context = ConversationContext()
        
        session.context.add_message(MessageRole.USER, "Hello")
        assert session.turn_count == 1
        
        session.context.add_message(MessageRole.ASSISTANT, "Hi!")
        assert session.turn_count == 1
        
        session.context.add_message(MessageRole.USER, "How are you?")
        assert session.turn_count == 2

    def test_session_to_dict(self):
        """测试转换为字典"""
        session = Session(user_id="user123")
        data = session.to_dict()
        
        assert data["user_id"] == "user123"
        assert data["state"] == "idle"
        assert "id" in data
        assert "created_at" in data


class TestAgentState:
    """测试Agent状态"""

    def test_state_values(self):
        """测试状态值"""
        assert AgentState.IDLE.value == "idle"
        assert AgentState.THINKING.value == "thinking"
        assert AgentState.ACTING.value == "acting"
        assert AgentState.WAITING_TOOL.value == "waiting_tool"


class TestAgent:
    """测试Agent"""

    @pytest.fixture
    def agent(self):
        """创建Agent实例"""
        return Agent(
            name="TestAgent",
            system_prompt="You are a helpful assistant.",
            max_turns=10
        )

    def test_agent_creation(self, agent):
        """测试创建Agent"""
        assert agent.name == "TestAgent"
        assert agent.system_prompt == "You are a helpful assistant."
        assert agent.max_turns == 10
        assert agent._sessions == {}

    def test_create_session(self, agent):
        """测试创建会话"""
        start_time = time.time()
        session = agent.create_session(user_id="user123")
        elapsed = (time.time() - start_time) * 1000
        
        assert elapsed < 100
        
        assert session.user_id == "user123"
        assert session.context is not None
        assert session.working_memory is not None
        assert session.id in agent._sessions

    def test_create_multiple_sessions(self, agent):
        """测试创建多个会话"""
        sessions = [agent.create_session(user_id=f"user{i}") for i in range(10)]
        
        ids = [s.id for s in sessions]
        assert len(ids) == len(set(ids))

    def test_get_session(self, agent):
        """测试获取会话"""
        session = agent.create_session(user_id="user123")
        
        retrieved = agent.get_session(session.id)
        assert retrieved is not None
        assert retrieved.id == session.id

    def test_get_nonexistent_session(self, agent):
        """测试获取不存在的会话"""
        session = agent.get_session("nonexistent-id")
        assert session is None

    def test_delete_session(self, agent):
        """测试删除会话"""
        session = agent.create_session(user_id="user123")
        
        result = agent.delete_session(session.id)
        assert result is True
        assert agent.get_session(session.id) is None

    def test_delete_nonexistent_session(self, agent):
        """测试删除不存在的会话"""
        result = agent.delete_session("nonexistent-id")
        assert result is False

    def test_list_sessions(self, agent):
        """测试列出会话"""
        agent.create_session(user_id="user1")
        agent.create_session(user_id="user2")
        agent.create_session(user_id="user1")
        
        all_sessions = agent.list_sessions()
        assert len(all_sessions) == 3
        
        user1_sessions = agent.list_sessions(user_id="user1")
        assert len(user1_sessions) == 2

    def test_reset_session(self, agent):
        """测试重置会话"""
        session = agent.create_session(user_id="user123")
        
        session.context.add_message(MessageRole.USER, "Hello")
        session.context.add_message(MessageRole.ASSISTANT, "Hi!")
        
        result = agent.reset_session(session.id)
        
        assert result is True
        assert len(session.context.messages) == 0
        assert session.state == AgentState.IDLE

    def test_set_llm(self, agent):
        """测试设置LLM"""
        mock_llm = MagicMock()
        mock_llm.provider = "openai"
        mock_llm.default_model = "gpt-4o"
        
        agent.set_llm(mock_llm)
        
        assert agent.llm is mock_llm
        assert agent.provider == "openai"
        assert agent.model == "gpt-4o"

    def test_add_tool(self, agent):
        """测试添加工具"""
        async def my_tool(arg: str) -> str:
            return f"Result: {arg}"
        
        agent.add_tool(name="my_tool", handler=my_tool, description="A test tool")
        
        # 注意：工具注册到全局注册表
        from agentframe.tools.registry import get_registry
        tool = get_registry().get_tool("my_tool")
        assert tool is not None
        assert tool.name == "my_tool"


class TestConversationContext:
    """测试对话上下文"""

    def test_add_message(self):
        """测试添加消息"""
        context = ConversationContext()
        
        context.add_message(MessageRole.USER, "Hello")
        assert len(context.messages) == 1
        assert context.messages[0].content == "Hello"

    def test_get_messages(self):
        """测试获取消息"""
        context = ConversationContext(system_prompt="You are helpful.")
        
        context.add_message(MessageRole.USER, "Hi")
        context.add_message(MessageRole.ASSISTANT, "Hello!")
        
        messages = context.get_messages()
        
        assert len(messages) == 3
        assert messages[0].role == MessageRole.SYSTEM
        assert messages[1].role == MessageRole.USER

    def test_get_last_n_messages(self):
        """测试获取最近消息"""
        context = ConversationContext()
        
        for i in range(10):
            context.add_message(MessageRole.USER, f"Message {i}")
        
        messages = context.get_last_n_messages(3)
        
        assert len(messages) == 3
        assert messages[0].content == "Message 7"
        assert messages[2].content == "Message 9"


class TestContextWindow:
    """测试上下文窗口"""

    def test_truncate_strategy(self):
        """测试截断策略"""
        window = ContextWindow(max_messages=5, strategy="truncate")
        
        context = ConversationContext()
        for i in range(20):
            context.add_message(MessageRole.USER, f"Message {i}")
        
        new_context = window.fit(context)
        
        assert len(new_context.messages) <= 5

    def test_max_messages(self):
        """测试最大消息数"""
        window = ContextWindow(max_messages=3)
        
        context = ConversationContext()
        for i in range(10):
            context.add_message(MessageRole.USER, f"Message {i}")
        
        new_context = window.fit(context)
        
        assert len(new_context.messages) <= 3


class TestWorkingMemory:
    """测试工作记忆"""

    def test_add_observation(self):
        """测试添加观察"""
        memory = WorkingMemory()
        
        memory.add_observation("Saw a red car")
        assert len(memory.observations) == 1

    def test_add_plan_step(self):
        """测试添加计划步骤"""
        memory = WorkingMemory()
        
        memory.add_plan_step("Step 1")
        memory.add_plan_step("Step 2")
        
        assert len(memory.plan) == 2

    def test_complete_plan_step(self):
        """测试完成计划步骤"""
        memory = WorkingMemory()
        memory.add_plan_step("Step 1")
        memory.add_plan_step("Step 2")
        
        completed = memory.complete_plan_step()
        
        assert completed == "Step 1"
        assert len(memory.plan) == 1

    def test_store_and_get_result(self):
        """测试存储和获取结果"""
        memory = WorkingMemory()
        
        memory.store_result("answer", 42)
        assert memory.get_result("answer") == 42

    def test_clear(self):
        """测试清空"""
        memory = WorkingMemory()
        memory.task = "Test task"
        memory.add_observation("Obs 1")
        memory.store_result("key", "value")
        
        memory.clear()
        
        assert memory.task is None
        assert len(memory.observations) == 0
        assert len(memory.results) == 0