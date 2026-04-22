"""API Module - API层

提供FastAPI REST API接口。
对应 PRD 7.1 和 SPEC 5.1
"""

from agentframe.api.routes import create_app

__all__ = ["create_app"]
