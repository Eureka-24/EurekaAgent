"""API Tests - API层测试

测试REST API接口功能。
对应 PRD 验收标准 7.1.1, 7.1.2

运行: pytest tests/unit/test_api.py -v
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from agentframe.api.routes import create_app
from agentframe.core.agent import Agent
from agentframe.core.session import AgentState
from agentframe.llm.base import Response


class TestAPIHealth:
    """测试健康检查"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        app = create_app()
        return TestClient(app)

    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestSessionAPI:
    """测试会话API"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        app = create_app()
        return TestClient(app)

    def test_create_session(self, client):
        """测试创建会话"""
        response = client.post(
            "/sessions",
            json={"user_id": "test_user", "metadata": {"source": "test"}}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["user_id"] == "test_user"

    def test_list_sessions(self, client):
        """测试列出会话"""
        client.post("/sessions", json={"user_id": "user1"})
        client.post("/sessions", json={"user_id": "user2"})
        
        response = client.get("/sessions")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    def test_get_nonexistent_session(self, client):
        """测试获取不存在的会话"""
        response = client.get("/sessions/nonexistent-id")
        assert response.status_code == 404


class TestChatAPI:
    """测试对话API"""

    @pytest.fixture
    def mock_agent(self):
        """创建模拟Agent"""
        agent = MagicMock(spec=Agent)
        
        mock_session = MagicMock()
        mock_session.id = "test-session-id"
        mock_session.user_id = "test_user"
        mock_session.state = AgentState.IDLE
        mock_session.turn_count = 0
        
        agent.create_session.return_value = mock_session
        agent.get_session.return_value = mock_session
        agent.chat = AsyncMock(return_value=Response(
            content="Hello!",
            model="test",
            finish_reason="stop"
        ))
        
        return agent

    @pytest.fixture
    def client(self, mock_agent):
        """创建测试客户端"""
        app = create_app(agent=mock_agent)
        return TestClient(app)

    def test_chat_without_session(self, client):
        """测试不带session_id的对话"""
        response = client.post(
            "/chat",
            json={"message": "Hello!"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data


class TestToolAPI:
    """测试工具API"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        app = create_app()
        return TestClient(app)

    def test_list_tools(self, client):
        """测试列出工具"""
        response = client.get("/tools")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_register_tool(self, client):
        """测试注册工具"""
        response = client.post(
            "/tools",
            json={
                "name": "test_tool",
                "description": "A test tool",
                "parameters": {
                    "type": "object",
                    "properties": {"arg1": {"type": "string"}},
                    "required": ["arg1"]
                }
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test_tool"

    def test_register_duplicate_tool(self, client):
        """测试重复注册"""
        client.post("/tools", json={
            "name": "dup_tool",
            "description": "Test",
            "parameters": {"type": "object", "properties": {}}
        })
        
        response = client.post("/tools", json={
            "name": "dup_tool",
            "description": "Test 2",
            "parameters": {"type": "object", "properties": {}}
        })
        
        assert response.status_code == 409
